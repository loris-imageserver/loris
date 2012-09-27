#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`loris` -- WSGI JPEG 2000 Server
=====================================
.. module:: loris
   :platform: Unix
   :synopsis: Implements IIIF 1.0 <http://www-sul.stanford.edu/iiif/image-api> 
   level 1 and most of level 2 

.. moduleauthor:: Jon Stroop <jstroop@princeton.edu>

"""

from collections import deque
from datetime import datetime
from decimal import Decimal, getcontext
from deepzoom import DeepZoomImageDescriptor
from random import choice
from string import ascii_lowercase, digits
from sys import exit, stderr
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.http import http_date, parse_date
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.wrappers import Request, Response
import ConfigParser
import logging
import logging.config
import os
import struct
import subprocess
import urlparse

def create_app(test=False):
	"""Create an instance of :class: `Loris`
	:param test: For unit tests, changes from configured dirs to test dirs.
	:type test: bool.
	"""
	global logr
	global conf_file
	global host_dir
	try:
		# Logging
		host_dir = os.path.abspath(os.path.dirname(__file__))
		conf_file = os.path.join(host_dir, 'loris.conf')
		logging.config.fileConfig(conf_file)
		if test:
			logr = logging.getLogger('loris_test')
		else:
			logr = logging.getLogger('loris')
		app = Loris(test)
		return app
	except Exception,e:
		stderr.write(e.message)
		exit(1)


class Loris(object):
	def __init__(self, test=False):
		"""The application. Generally these should be instantiated with 
		:func:`create_app`.

		:param test: For unit tests, changes from configured dirs to test dirs. 
		"""
		self.test=test

		# Configuration - Everything else
		_conf = ConfigParser.RawConfigParser()
		_conf.read(conf_file)

		# options
		self.decimal_precision = _conf.getint('options', 'decimal_precision')
		getcontext().prec = self.decimal_precision
		self.use_201 = _conf.getboolean('options', 'use_201')
		self.cache_px_only = _conf.getboolean('options', 'cache_px_only')
		self.use_415 = _conf.getboolean('options', 'use_415')
		self.default_format = _conf.get('options', 'default_format')
		self.enable_cache = _conf.getboolean('options', 'enable_cache')

		# utilities
		self.convert_cmd = _conf.get('utilities', 'convert')
		self.mkfifo_cmd = _conf.get('utilities', 'mkfifo')
		self.kdu_expand_cmd = _conf.get('utilities', 'kdu_expand')
		self.kdu_libs = _conf.get('utilities', 'kdu_libs')
		self.rm_cmd = _conf.get('utilities', 'rm')

		# directories
		host_dir = os.path.abspath(os.path.dirname(__file__))
		self.tmp_dir = ''
		self.cache_root = ''
		self.src_images_root = ''
		if self.test:
			self.tmp_dir = _conf.get('directories', 'test_tmp')
			self.cache_root = _conf.get('directories', 'test_cache_root')
			self.src_images_root = os.path.join(host_dir, 'test_img') 
		else:
			self.tmp_dir = _conf.get('directories', 'tmp')
			self.cache_root = _conf.get('directories', 'cache_root')
			self.src_images_root = _conf.get('directories', 'src_img_root')

		try:
			for d in (self.tmp_dir, self.cache_root):
				if not os.path.exists(d):
					os.makedirs(d, 0755)
					logr.info("Created " + d)
				if not os.access(d, os.R_OK) and os.access(d, os.W_OK):
					msg = d  + ' must exist and be readable and writable'
					raise Exception(msg)


		except Exception, e:
			msg = 'Exception setting up directories: ' 
			msg += e.message
			logr.fatal(msg)
			exit(1)
		
		# compliance and help links
		compliance_uri = _conf.get('compliance', 'uri')
		help_uri = _conf.get('compliance', 'help_uri')
		self.link_hdr = '<' + compliance_uri  + '>;rel=profile,'
		self.link_hdr += '<' + help_uri + '>;rel=help'

		converters = {
				'region' : RegionConverter,
				'size' : SizeConverter,
				'rotation' : RotationConverter
			}
		self.url_map = Map([

			Rule('/<path:ident>/info.<format>', endpoint='get_img_metadata'),
			Rule('/<path:ident>/info', endpoint='get_img_metadata'),
			Rule('/<path:ident>/<region:region>/<size:size>/<rotation:rotation>/<any(native, color, grey, bitonal):quality>.<format>', endpoint='get_img'),
			Rule('/<path:ident>/<region:region>/<size:size>/<rotation:rotation>/<any(native, color, grey, bitonal):quality>', endpoint='get_img'),
			Rule('/<path:ident>.xml', endpoint='get_deepzoom_desc'),
			Rule('/<path:ident>/<int:level>/<int:x>_<int:y>.jpg', endpoint='get_img_for_seajax'),
			Rule('/favicon.ico', endpoint='get_favicon')
		], converters=converters)
	
	def dispatch_request(self, request):
		"""
		Dispatch the request to the proper method. By convention, the endpoint,
		(i.e. the method to be called) is named 'on_<method>'.
		"""

		adapter = self.url_map.bind_to_environ(request.environ)
		try:
			endpoint, values = adapter.match()
			dispatch_to_method = 'on_' + endpoint
			
			logr.info('Dispatching to ' + dispatch_to_method)
			return getattr(self, dispatch_to_method)(request, **values)

		# Any exceptions related to parsing the requests into parameter objects
		# should end up here.
		except LorisException, e:
		 	mime = 'text/xml'
		 	status = e.http_status
		 	resp = e.to_xml()
		 	headers = Headers()
			headers.add('Link', self.link_hdr)
			return Response(resp, status=status, mimetype=mime, headers=headers)

		except Exception, e:
			pe = LorisException(400, '', e.message)
			mime = 'text/xml'
			status = pe.http_status
		 	resp = pe.to_xml()
		 	headers = Headers()
			headers.add('Link', self.link_hdr)
			return Response(resp, status=status, mimetype=mime, headers=headers)


	def on_get_favicon(self, request):
		f = os.path.join(host_dir, 'favicon.ico')
		return Response(f, content_type='image/x-icon')
		
	def on_get_img_metadata(self, request, ident, format=None):
		resp = None
		status = None
		mime = None
		headers = Headers()
		headers.add('Link', self.link_hdr)
		headers.add('Cache-Control', 'public')

		try:
			if format == 'json': mime = 'text/json'
			elif format == 'xml': mime = 'text/xml'
			elif request.headers.get('accept') == 'text/json':
				format = 'json'
				mime = 'text/json'
			elif request.headers.get('accept') == 'text/xml':
				format = 'xml'
				mime = 'text/xml'
			else:
				msg = 'Only XML or json are available'
				raise FormatNotSupportedException(415, format, msg)
				
			img_path = self._resolve_identifier(ident)
			
			if not os.path.exists(img_path):
				msg = 'Identifier does not resolve to an image.'
				raise LorisException(404, ident, msg)
			
			cache_dir = os.path.join(self.cache_root, ident)
			cache_path = os.path.join(cache_dir, 'info.') + format
			

			# check the cache
			if os.path.exists(cache_path) and self.enable_cache == True:
				status = self._check_cache(cache_path, request, headers)
				resp = file(cache_path) if status == 200 else None
			else:
				status = 201 if self.use_201 else 200
				info = ImgInfo.fromJP2(img_path, ident)
				info.id = ident
				resp = info.marshal(to=format)
				length = len(resp)

				if not os.path.exists(cache_dir): 
					os.makedirs(cache_dir, 0755)

				logr.debug('made ' + cache_dir)

				if self.enable_cache:
					f = open(cache_path, 'w')
					f.write(resp)
					f.close()
					logr.info('Created: ' + cache_path)

				headers.add('Last-Modified', http_date())
				headers.add('Content-Length', length)

		except LorisException as e:
		 	mime = 'text/xml'
		 	status = e.http_status
		 	resp = e.to_xml()

		except Exception as e:
			# should be safe to assume it's the server's fault.
		 	pe = LorisException(500, '', e.message)
		 	mime = 'text/xml'
		 	status = pe.http_status
		 	resp = pe.to_xml()

		finally:
			return Response(resp, status=status, content_type=mime, headers=headers)

	def on_get_deepzoom_desc(self, request, ident):
		resp = None
		status = None
		mime = 'text/xml'
		headers = Headers()
		headers.add('Link', self.link_hdr)
		headers.add('Cache-Control', 'public')

		try:
			cache_dir = os.path.join(self.cache_root, ident)
			cache_path = os.path.join(cache_dir,  'sd.xml')

			# check the cache
			if os.path.exists(cache_path) and self.enable_cache:
				status = self._check_cache(cache_path, request, headers)
				resp = file(cache_path) if status == 200 else None
			else:
				status = 201 if self.use_201 else 200
				img_path = self._resolve_identifier(ident)
				info = ImgInfo.fromJP2(img_path, ident)

				dzid = DeepZoomImageDescriptor(width=info.width, height=info.height, \
					tile_size=256, tile_overlap=0, tile_format='jpg')
				
				resp = dzid.marshal()

				length = len(resp)

				if not os.path.exists(cache_dir): 
					os.makedirs(cache_dir, 0755)

				logr.debug('made ' + cache_dir)

				if self.enable_cache:
					f = open(cache_path, 'w')
					f.write(resp)
					f.close()
					logr.info('Created: ' + cache_path)

				headers.add('Last-Modified', http_date())
				headers.add('Content-Length', length)

		except Exception as e:
			# should be safe to assume it's the server's fault.
		 	pe = LorisException(500, '', e.message)
		 	mime = 'text/xml'
		 	status = pe.http_status
		 	resp = pe.to_xml()

		finally:
			return Response(resp, status=status, content_type=mime, headers=headers)


	def on_get_img(self, request, ident, region, size, rotation, quality, format=None):
		"""
		Get an image based on the *Parameter objects and values returned by the 
		converters.

		:param request: a werkzeug Request object
		:type request: Request

		:param ident: the image identifier
		:type ident: str

		:param region
		:type region: RegionParameter

		:param size
		:type size: SizeParameter

		:param rotation: rotation of the image (multiples of 90 for now)
		:type rotation: integer

		:param quality: 'native', 'color', 'grey', 'bitonal'
		:type quality: str

		:param format - 'jpg' or 'png'
		:type format: str

		:returns: Response -- body is either an image, XML (err), or None if 304
		"""

		resp = None
		status = None
		mime = None
		headers = Headers()
		headers.add('Link', self.link_hdr)
		headers.add('Cache-Control', 'public')

		# Support accept headers and poor-man's conneg by file extension. 
		# By configuration we allow either a default format, or the option
		# to return a 415 if neither a file extension or Accept header are 
		# supplied.
		# Cf. 4.5: ... If the format is not specified in the URI ....
		if not format and not self.use_415:	format = self.default_format

		if format == 'jpg':	
			mime = 'image/jpeg'
		elif format == 'png': 
			mime = 'image/png'
		elif request.headers.get('accept') == 'image/jpeg':
			format = 'jpg'
			mime = 'image/jpeg'
		elif request.headers.get('accept') == 'image/png':
			format = 'png'
			mime = 'image/png'
		else:
			msg = 'The format requested is not supported by this service.'
			raise FormatNotSupportedException(415, format, msg)
		
		img_dir = os.path.join(self.cache_root, ident, region.url_value, size.url_value, rotation.url_value)
		img_path = os.path.join(img_dir, quality + '.' + format)
		logr.debug('img_dir: ' + img_dir)
		logr.debug('img_path: ' + img_path)
	
		# check the cache
		if  self.enable_cache == True and os.path.exists(img_path):
			status = self._check_cache(img_path, request, headers)
			resp = file(img_path) if status == 200 else None
		else:
			try:
				if not os.path.exists(img_dir):	
					os.makedirs(img_dir, 0755)
				logr.info('Made directory: ' + img_dir)
				img_success = self._derive_img_from_jp2(ident, img_path, region, size, rotation, quality, format)
				status = 201 if self.use_201 else 200
			 	headers.add('Content-Length', os.path.getsize(img_path))
				headers.add('Last-Modified', http_date()) # now
				resp = file(img_path)
			except LorisException, e:
				headers.remove('Last-Modified')
				mime = 'text/xml'
			 	status = e.http_status
		 		resp = e.to_xml()

 		return Response(resp, status=status, content_type=mime, headers=headers, direct_passthrough=True)

 	def _check_cache(self, resource_path, request, headers):
 		"""Check the cache for a resource, update the headers object that we're 
 		passing a reference to, and return the HTTP status that should be 
 		returned.

 		:param resource_path: path to a file on the file system
 		:type resource_path: str

 		:param request: the current request object
 		:type request: Request

 		:param headers: the headers object that will ultimately be returned with the request
 		:type headers: Headers
 		"""
		last_change = datetime.utcfromtimestamp(os.path.getctime(resource_path))
		ims_hdr = request.headers.get('If-Modified-Since')
		ims = parse_date(ims_hdr)
		if (ims and ims > last_change) or not ims:
			status = 200
			# resp = file(img_path)
			length = length = os.path.getsize(resource_path) 
			headers.add('Content-Length', length)
			headers.add('Last-Modified', http_date(last_change))
			logr.info('Read: ' + resource_path)
		else:
			status = 304
			headers.remove('Content-Type')
			headers.remove('Cache-Control')
		return status


	def _derive_img_from_jp2(self, ident, out_path, region, size, rotation, quality, format):
		"""
		out_path is the output path
		"""
		try:
			fifo_path = ''
			# We may not want to read this from the file every time, though 
			# it is pretty fast. Runtime cache? In memory dicts and Shelve/
			# pickle are not thread safe for writing (and probably wouldn't
			# scale anyway)
			# ZODB? : http://www.zodb.org/
			# Kyoto Cabinet? : http://fallabs.com/kyotocabinet/
			jp2 = self._resolve_identifier(ident)
			info = ImgInfo.fromJP2(jp2, ident)
			
			# Do some checking early to avoid starting to build the shell 
			# outs
			if quality not in info.qualities:
				msg = 'This quality is not available for this image.'
				raise LorisException(400, quality, msg)

			if self.cache_px_only and region.mode == 'pct':
				top_px = int(round(Decimal(region.y) * Decimal(info.height) / Decimal(100.0)))
				logr.debug('top_px: ' + str(top_px))
				left_px = int(round(Decimal(region.x) * info.width / Decimal(100.0)))
				logr.debug('left_px: ' + str(left_px))
				height_px = int(round(Decimal(region.h) * info.height / Decimal(100.0)))
				logr.debug('height_px: ' + str(height_px))
				width_px = int(round(Decimal(region.w) * info.width / Decimal(100.0)))
				logr.debug('width_px: ' + str(width_px))
				new_url_value = ','.join(map(str, (left_px, top_px, width_px, height_px)))
				new_region_param = RegionParameter(new_url_value)
				logr.info('pct region request revised to ' + new_url_value)
				region_kdu_arg = new_region_param.to_kdu_arg(info)
			else:
				region_kdu_arg = region.to_kdu_arg(info)
			

			# Start building and executing commands.
			# This could get a lot more sophisticated, jp2 levels for 
			# certain sizes, etc.; different utils for different formats, 
			# use cjpeg for jpegs, and so on.

			# Make a named pipe for the temporary bitmap
			fifo_path = os.path.join(self.tmp_dir, self.random_str(10) + '.bmp')
			mkfifo_call= self.mkfifo_cmd + ' ' + fifo_path
			
			logr.debug('Calling ' + mkfifo_call)
			subprocess.check_call(mkfifo_call, shell=True)
			logr.debug('Done (' + mkfifo_call + ')')

			# Make and call the kdu_expand cmd
			kdu_expand_call = ''
			kdu_expand_call += self.kdu_expand_cmd + ' -quiet '
			kdu_expand_call += '-i ' + jp2 
			kdu_expand_call += ' -o ' + fifo_path
			kdu_expand_call += ' ' + region_kdu_arg
			
			logr.debug('Calling ' + kdu_expand_call)
			kdu_expand_proc = subprocess.Popen(kdu_expand_call, \
				shell=True, \
				bufsize=-1, \
				stderr=subprocess.PIPE,\
				env={"LD_LIBRARY_PATH" : self.kdu_libs})

			# make and call the convert command

			convert_call = ''
			convert_call = self.convert_cmd + ' '
			convert_call += fifo_path + ' '
			convert_call += size.to_convert_arg() + ' '
			convert_call += rotation.to_convert_arg() + ' '

			if format == 'jpg':
			 	convert_call += '-quality 90 '
			if format == 'png':
				convert_call += '-colors 256 -quality 00 ' 

			if quality == 'grey' and info.native_quality != 'grey':
				convert_call += '-colorspace gray -depth 8 '
			if quality == 'bitonal' and info.native_quality != 'bitonal':
				convert_call += '-colorspace gray -depth 1 '

			convert_call += out_path
			
			logr.debug('Calling ' + convert_call)
			convert_proc = subprocess.Popen(convert_call, \
				shell=True, \
				bufsize=-1, \
				stderr=subprocess.PIPE)
			
			convert_exit = convert_proc.wait()
			if convert_exit != 0:
				msg = '. '.join(convert_proc.stderr)
				raise LorisException(500, '', msg)
			logr.debug('Done (' + convert_call + ')')
			
			kdu_exit = kdu_expand_proc.wait()
			if kdu_exit != 0:
				msg = ''
				for line in kdu_expand_proc.stderr:
					msg += line + '. '

				raise LorisException(500, '', msg)

			logr.debug('Terminated ' + kdu_expand_call)
			logr.info("Created: " + out_path)

			return 0
		except Exception, e:
			raise LorisException(500, '', e.message)
		finally:
			# Make and call rm $fifo
			if os.path.exists(fifo_path):
				rm_fifo_call = self.rm_cmd + ' ' + fifo_path
				logr.debug('Calling ' + rm_fifo_call)
				subprocess.call(rm_fifo_call, shell=True)
				logr.debug('Done (' + rm_fifo_call + ')')

	def on_get_img_for_seajax(self, request, ident, level, x, y):
		"""Use the `deepzoom.py` module to make tiles for Seadragon (and 
		optionally cache them and according to IIIF's cache syntax and make
		symlinks).

		URLs (and symlinked file paths) look like `/level/x_y.jpg`

		:param request: Werkzeug's request object
		:type request: Request
		:param ident: the image identifier
		:type ident: string
		:param level: seadragon's notion of a zoom level
		:type level: int
		:param x: the zero-based index of the tile on the x-axis, starting from upper-left
		:type x: int
		:param y: the zero-based index of the tile on the y-axis, starting from upper-left
		:type y: int
		"""
		img_dir = os.path.join(self.cache_root, ident, str(level))
		file_name = str(x) + '_' + str(y) + '.jpg'
		img_path = os.path.join(img_dir, file_name)
		logr.debug('seadragon img_dir: ' + img_dir)
		logr.debug('seadragon img_path: ' + img_path)

		# check the cache
		if  self.enable_cache == True and os.path.exists(img_path):
			last_change = datetime.utcfromtimestamp(os.path.getctime(img_path))
			ims_hdr = request.headers.get('If-Modified-Since')
			ims = parse_date(ims_hdr)
			if (ims and ims > last_change) or not ims:
				status = 200
				resp = file(img_path)
				length = length = os.path.getsize(img_path) 
				headers.add('Content-Length', length)
				headers.add('Last-Modified', http_date(last_change))
				logr.info('Read: ' + img_path)
			else:
				status = 304
				headers.remove('Content-Type')
				headers.remove('Cache-Control')
				resp = None
		else:
			# We're going to build a 301 (see other)
			# 1. calculate the size of the image
			# 2. calculate the region (adjusted for size)
			# 3. build the path to the image
			pass


	def _resolve_identifier(self, ident):
		"""
		Given the identifier of an image, resolve it to an actual path. This
		would need to be overridden to suit different environments.
		
		This simple version just prepends a constant path to the identfier
		supplied, and appends a file extension, resulting in an absolute path 
		on the filesystem.
		"""
		return os.path.join(self.src_images_root, ident + '.jp2')

	def random_str(self, size):
		chars = ascii_lowercase + digits
		return ''.join(choice(chars) for x in range(size))

	def wsgi_app(self, environ, start_response):
		request = Request(environ)
		response = self.dispatch_request(request)
		return response(environ, start_response)

	def __call__(self, environ, start_response):
		return self.wsgi_app(environ, start_response)

class RegionConverter(BaseConverter):
	"""
	Custom converter for the region paramaters as specified.
	
	@see http://library.stanford.edu/iiif/image-api/#region
	
	@return: A new RegionParameter object.
	
	"""
	def __init__(self, url_map):
		super(RegionConverter, self).__init__(url_map)
		self.regex = '[^/]+'

	def to_python(self, value):
		return RegionParameter(value)

	def to_url(self, value):
		return str(value)

class RegionParameter(object):
	"""
	self.mode is always one of 'full', 'pct', or 'pixel'
	"""
	def __init__(self, url_value):
		self.url_value = url_value
		self.mode = ''
		self.x, self.y, self.w, self.h = [None, None, None, None]

		if self.url_value == 'full':
			self.mode = 'full'
		else:
			try:
				if url_value.split(':')[0] == 'pct':
					self.mode = 'pct'
					pct_value = url_value.split(':')[1]
					logr.debug('Percent dimensions request: ' + pct_value)
					# floats!
					dimensions = map(float, pct_value.split(','))
					if any(n > 100.0 for n in dimensions):
						msg = 'Percentages must be less than or equal to 100.'
						raise BadRegionSyntaxException(400, url_value, msg)
					if any((n <= 0) for n in dimensions[2:]):
						msg = 'Width and Height Percentages must be greater than 0.'
						raise BadRegionSyntaxException(400, url_value, msg)
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, url_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
				else:
					self.mode = 'pixel'
					logr.debug('Pixel dimensions request: ' + url_value)
					
					try:
						dimensions = map(int, url_value.split(','))
					# ints only!
					except ValueError, v :
						v.message += ' (Pixel dimensions must be integers.)'
						raise
					if any(n <= 0 for n in dimensions[2:]):
						msg = 'Width and height must be greater than 0'
						raise BadRegionSyntaxException(400, url_value, msg)
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, url_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
			except Exception, e :
				msg = 'Region syntax not valid. ' + e.message
				raise BadRegionSyntaxException(400, url_value, msg)

	def to_kdu_arg(self, img_info):
		"""kdu wants \{<top>,<left>\},\{<height>,<width>\} (shell syntax), as 
		decimals between 0 and 1.
		IIIF supplies left[x], top[y], witdth[w], height[h].
		"""
		# If pixels and pcts are both used, then reduce the size of the cache 
		# by we could only storing pixel sizes and send a 303 for pct based 
		# requests. Could do it by catching pct requests, calculating the pixels 
		# and raising an exception that results in the redirect.

		cmd = ''
		if self.mode != 'full':
			cmd = '-region '

			# First: convert into decimals (we'll pass these to kdu after
			# we test them)
			top = Decimal(self.y) / Decimal(100.0) if self.mode == 'pct' else Decimal(self.y) / img_info.height
			left = Decimal(self.x) / Decimal(100.0) if self.mode == 'pct' else Decimal(self.x) / img_info.width
			height = Decimal(self.h) / Decimal(100.0) if self.mode == 'pct' else Decimal(self.h) / img_info.height
			width = Decimal(self.w) / Decimal(100.0) if self.mode == 'pct' else Decimal(self.w) / img_info.width

			# "If the request specifies a region which extends beyond the 
			# dimensions of the source image, then the service should return an 
			# image cropped at the boundary of the source image."
			if (width + left) > Decimal(1.0): 
				width = Decimal(1.0) - Decimal(left)
				logr.debug('Width adjusted to: ' + str(width))
			if (top + height) > Decimal(1.0): 
				height = Decimal(1.0) - Decimal(top)
				logr.debug('Height adjusted to: ' + str(height))
			# Catch OOB errors:
			# top and left
			if any(axis < 0 for axis in (top, left)):
				msg = 'x and y region paramaters must be 0 or greater'
				raise BadRegionRequestException(400, self.url_value, msg)
			if left >= Decimal(1.0):
				msg = 'Region x parameter is out of bounds.\n'
				msg += str(self.x) + ' was supplied and image width is ' 
				msg += str(img_info.width)
				raise BadRegionRequestException(400, self.url_value, msg)
			if top >= Decimal(1.0):
				msg = 'Region y parameter is out of bounds.\n'
				msg += str(self.y) + ' was supplied and image height is ' 
				msg += str(img_info.height)
				raise BadRegionRequestException(400, self.url_value, msg)
			cmd += '\{%s,%s\},\{%s,%s\}' % (top, left, height, width)
			logr.debug('kdu region parameter: ' + cmd)
		return cmd
	

class SizeConverter(BaseConverter):
	"""
	Custom converter for the size paramaters as specified.
	
	Note that force_aspect is only supplied when we have a w AND h, otherwise it
	is None.
	
	@see http://library.stanford.edu/iiif/image-api/#size
	
	@return: dictionary with these entries: is_full, force_aspect, pct, 
	level, w, h. The is_full and force_aspect entries are bools, the remaining 
	are ints.
	
	"""
	def __init__(self, url_map):
		super(SizeConverter, self).__init__(url_map)
		self.regex = '[^/]+'
	
	def to_python(self, value):
		return SizeParameter(value)

	def to_url(self, value):
		return str(value) # ??

class SizeParameter(object):
	"""
	self.mode is always one of 'full', 'pct', or 'pixel'
	"""
	def __init__(self, url_value):
		self.url_value = url_value
		self.mode = 'pixel'
		self.force_aspect = None
		self.pct = None
		self.w, self.h = [None, None]
		try:
			if self.url_value == 'full':
				self.mode = 'full'

			elif self.url_value.startswith('pct:'):
				self.mode = 'pct'
				try:
					self.pct = float(self.url_value.split(':')[1])
					if self.pct > 100:
						msg = 'Percentage supplied is greater than 100. '
						msg += 'Upsampling is not supported.'
						raise BadSizeSyntaxException(400, self.url_value, msg)
					if self.pct <= 0:
						msg = 'Percentage supplied is less than 0. '
						raise BadSizeSyntaxException(400, self.url_value, msg)
				except:
					raise
			elif self.url_value.endswith(','):
				try:
					self.w = int(self.url_value[:-1])
				except:
					raise
			elif self.url_value.startswith(','):
				try:
					self.h = int(self.url_value[1:])
				except:
					raise
			elif self.url_value.startswith('!'):
				self.force_aspect = False
				try:
					self.w, self.h = [int(d) for d in self.url_value[1:].split(',')]
				except:
					raise
			else:
				self.force_aspect = True
				try:
					self.w, self.h = [int(d) for d in self.url_value.split(',')]
				except:
					raise
		except ValueError, e:
			msg = 'Bad size syntax. ' + e.message
			raise BadSizeSyntaxException(400, self.url_value, msg)
		except Exception, e:
			msg = 'Bad size syntax. ' + e.message
			raise BadSizeSyntaxException(400, self.url_value, msg)
		
		if any((dim < 1 and dim != None) for dim in (self.w, self.h)):
			msg = 'Width and height must both be positive numbers'
			raise BadSizeSyntaxException(400, self.url_value, msg)
		
	def to_convert_arg(self):

		cmd = ''
		if self.url_value != 'full':
			cmd = '-resize '
			if self.mode == 'pct':
				cmd += str(self.pct) + '%'
			elif self.w and not self.h:
				cmd += str(self.w)
			elif self.h and not self.w:
				cmd += 'x' + str(self.h)
			# Note that IIIF and Imagmagick use '!' in opposite ways: to IIIF, 
			# the presense of ! means that the aspect ratio should be preserved,
			# to `convert` it means that it should be ignored
			elif self.w and self.h and not self.force_aspect:
				cmd +=  str(self.w) + 'x' + str(self.h) + '\>' # Don't upsample. Should this be configurable?
			elif self.w and self.h and self.force_aspect:
				cmd += str(self.w) + 'x' + str(self.h) + '!'

			else:
				msg = 'Could not construct a convert argument from ' + self.url_value
				raise BadSizeRequestException(500, msg)
		return cmd

class RotationConverter(BaseConverter):
	"""
	Custom converter for the rotation parameter.
	
	@see: http://library.stanford.edu/iiif/image-api/#rotation

	@return: a RotationParameter
	"""
	def __init__(self, url_map):
		super(RotationConverter, self).__init__(url_map)
		self.regex = '\-?\d+'

	def to_python(self, value):
		# Round. kdu can handle negatives values > 360 and < -360
		return RotationParameter(value)

	def to_url(self, value):
		return str(value)

class RotationParameter(object):
	"""docstring
	"""
	def __init__(self, url_value):
		self.url_value = url_value
		try:
			self.nearest_90 = int(90 * round(float(self.url_value) / 90))
		except Exception, e:
			raise BadRotationSyntaxException(400, self.url_value, e.message)

	def to_convert_arg(self):
		return '-rotate ' + str(self.nearest_90) if self.nearest_90 % 360 != 0 else ''

class ImgInfo(object):
	def __init__(self):
		self.id = id
		self.width = None
		self.height = None
		self.tile_width = None
		self.tile_height = None
		self.levels = None
		self.qualities = []
		self.native_quality = None
	
	# Other fromXXX methods could be defined
	
	@staticmethod
	def fromJP2(path, img_id):
		"""
		Get info about a JP2. There's enough going on here;
		make sure the file is available (exists and readable) before passing it.
		
		@see:  http://library.stanford.edu/iiif/image-api/#info
		"""
		info = ImgInfo()
		info.id = img_id
		info.qualities = ['native', 'bitonal']

		jp2 = open(path, 'rb')
		b = jp2.read(1)

		# Figure out color or greyscale. 
		# Depending color profiles; there's probably a better way (or more than
		# one anyway.)
		# see: JP2 I.5.3.3 Colour Specification box
		window =  deque([], 4)
		while ''.join(window) != 'colr':
			b = jp2.read(1)
			c = struct.unpack('c', b)[0]
			window.append(c)

		b = jp2.read(1)
		meth = struct.unpack('B', b)[0]
		jp2.read(2) # over PREC and APPROX, 1 byte each
		if meth == 1: # Enumerated Colourspace
			enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
			if enum_cs == 16:
				info.native_quality = 'color'
				info.qualities += ['grey', 'color']
			elif enum_cs == 17:
				info.native_quality = 'grey'
				info.qualities += ['grey']
		logr.debug('qualities: ' + str(info.qualities))

		b = jp2.read(1)
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) #skip over the SOC, 0x4F 
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x51: The SIZ marker segment
		if (ord(b) == 0x51):
			jp2.read(4) # get through Lsiz, Rsiz (16 bits each)
			info.width = int(struct.unpack(">HH", jp2.read(4))[1]) # Xsiz (32)
			info.height = int(struct.unpack(">HH", jp2.read(4))[1]) # Ysiz (32)
			logr.debug("width: " + str(info.width))
			logr.debug("height: " + str(info.height))
			jp2.read(8) # get through XOsiz , YOsiz  (32 bits each)
			info.tile_width = int(struct.unpack(">HH", jp2.read(4))[1]) # XTsiz (32)
			info.tile_height = int(struct.unpack(">HH", jp2.read(4))[1]) # YTsiz (32)
			logr.debug("tile width: " + str(info.tile_width))
			logr.debug("tile height: " + str(info.tile_height))	

		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x52: The COD marker segment
		if (ord(b) == 0x52):
			jp2.read(7) # through Lcod, Scod, SGcod (16 + 8 + 32 = 56 bits)
			info.levels = int(struct.unpack(">B", jp2.read(1))[0])
			logr.debug("levels: " + str(info.levels)) 
		jp2.close()
			
		return info
	
	def marshal(self, to):
		if to == 'xml': return self._to_xml()
		elif to == 'json': return self._to_json()
		else:
			raise Exception('Argument to marshal must be \'xml\' or \'json\'')

	def _to_xml(self):
		# cheap!
		x = '<?xml version="1.0" encoding="UTF-8"?>' + os.linesep
		x += '<info xmlns="http://library.stanford.edu/iiif/image-api/ns/">' + os.linesep
		x += '  <identifier>' + self.id + '</identifier>' + os.linesep
		x += '  <width>' + str(self.width) + '</width>' + os.linesep
		x += '  <height>' + str(self.height) + '</height>' + os.linesep
		x += '  <scale_factors>' + os.linesep
		for s in range(1, self.levels+1):
			x += '    <scale_factor>' + str(s) + '</scale_factor>' + os.linesep
		x += '  </scale_factors>' + os.linesep
		x += '  <tile_width>' + str(self.tile_width) + '</tile_width>' + os.linesep
		x += '  <tile_height>' + str(self.tile_height) + '</tile_height>' + os.linesep
		x += '  <formats>' + os.linesep
		x += '    <format>jpg</format>' + os.linesep
		x += '    <format>png</format>' + os.linesep
		x += '  </formats>' + os.linesep
		x += '  <qualities>' + os.linesep
		for q in self.qualities:
		 	x += '    <quality>' + q + '</quality>' + os.linesep
		x += '  </qualities>' + os.linesep
		x += '  <profile>http://library.stanford.edu/iiif/image-api/compliance.html#level1</profile>' + os.linesep
		x += '</info>' + os.linesep
		return x
	
	def _to_json(self):
		# cheaper!
		j = '{'
		j += '  "identifier" : "' + self.id + '", '
		j += '  "width" : ' + str(self.width) + ', '
		j += '  "height" : ' + str(self.height) + ', '
		j += '  "scale_factors" : [' + ", ".join(str(l) for l in range(1, self.levels+1)) + '], '
		j += '  "tile_width" : ' + str(self.tile_width) + ', '
		j += '  "tile_height" : ' + str(self.tile_height) + ', '
		j += '  "formats" : [ "jpg", "png" ], '
		j += '  "qualities" : [' + ", ".join('"'+q+'"' for q in self.qualities) + '], '
		j += '  "profile" : "http://library.stanford.edu/iiif/image-api/compliance.html#level1"'
		j += '}'
		return j

# This seems easier than http://werkzeug.pocoo.org/docs/exceptions/ because we
# have this custom XML body.
class LorisException(Exception):
	def __init__(self, http_status=404, supplied_value='', msg=''):
		"""
		"""
		super(LorisException, self).__init__(msg)
		self.http_status = http_status
		self.supplied_value = supplied_value

	def to_xml(self):
		r = '<?xml version="1.0" encoding="UTF-8" ?>\n'
		r += '<error xmlns="http://library.stanford.edu/iiif/image-api/ns/">\n'
		r += '  <parameter>' + self.supplied_value  + '</parameter>\n'
		r += '  <text>' + self.message + '</text>\n'
		r += '</error>\n'
		return r

class BadRegionSyntaxException(LorisException): pass
class BadRegionRequestException(LorisException): pass
class BadSizeSyntaxException(LorisException): pass
class BadSizeRequestException(LorisException): pass
class BadRotationSyntaxException(LorisException): pass
class FormatNotSupportedException(LorisException): pass

if __name__ == '__main__':
	'''Run the development server'''
	from werkzeug.serving import run_simple
	app = create_app(test=True)
	run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
