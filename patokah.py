#!/usr/bin/env python
# -*- coding: utf-8 -*-

from decimal import Decimal, getcontext
from random import choice
from string import ascii_lowercase, digits
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.wrappers import Request, Response
import ConfigParser
import logging
import logging.config
import os # TODO: only using makedirs, linsep, and path (I think)
import struct
import subprocess
import urlparse
abs_path = os.path.abspath(os.path.dirname(__file__))
conf_file = os.path.join(abs_path, 'patokah.conf') 
logging.config.fileConfig(conf_file)
logr = logging.getLogger('patokah')
logr.info("Logging initialized")

def create_app(test=False):
	app = Patokah(test)
	return app

# TODO: when we start to stream big files from the filesystem, see:
# http://stackoverflow.com/questions/5166129/how-do-i-stream-a-file-using-werkzeug

# TODO: make sure this is executable from the shell - tests had path trouble

class Patokah(object):
	def __init__(self, test=False):
		"""
		@param test: For unit tests, changes from configured dirs to test dirs. 
		"""
		# Configuration - Everything else
		_conf = ConfigParser.RawConfigParser()
		_conf.read(conf_file)

		# options
		self.decimal_precision = int(_conf.get('options', 'decimal_precision'))
		getcontext().prec = self.decimal_precision
		self.use_201 = bool(_conf.get('options', 'use_201'))
		self.cache_px_only = bool(_conf.get('options', 'cache_px_only'))
		self.use_415 = bool(_conf.get('options', 'use_415'))
		self.default_format = _conf.get('options', 'default_format')

		# utilities
		self.test=test
		self.convert_cmd = _conf.get('utilities', 'convert')
		self.mkfifo_cmd = _conf.get('utilities', 'mkfifo')
		self.kdu_expand_cmd = _conf.get('utilities', 'kdu_expand')
		self.kdu_compress_cmd = _conf.get('utilities', 'kdu_compress')
		self.rm_cmd = _conf.get('utilities', 'rm')

		# dirs		
		self.tmp_dir= _conf.get('directories', 'tmp')
		self.cache_root = _conf.get('directories', 'cache_root')
		self.src_images_root = ''
		if self.test:
			abs_path = os.path.abspath(os.path.dirname(__file__))
			self.src_images_root = os.path.join(abs_path, 'test_img') 
		else:
			self.src_images_root = _conf.get('directories', 'src_img_root')


		self.patoka_data_dir = os.path.join(abs_path, 'data')

		# compliance
		self.COMPLIANCE = _conf.get('compliance', 'uri')

		for d in (self.tmp_dir, self.cache_root):
			if not os.path.exists(d):
				os.makedirs(d, 0755)
				logr.info("Created " + d)

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
			Rule('/favicon.ico', endpoint='get_favicon')
		], converters=converters)
	
	def dispatch_request(self, request):
		"""
		Dispatch the request to the proper method. By convention, the endpoint,
		(i.e. the method to be called) is named 'on_<method>'.
		"""
		# TODO: exception handling. 
		adapter = self.url_map.bind_to_environ(request.environ)
		try:
			endpoint, values = adapter.match()
			dispatch_to_method = 'on_' + endpoint
			
			logr.info('Dispatching to ' + dispatch_to_method)
			return getattr(self, dispatch_to_method)(request, **values)

		except PatokahException, e:
		 	mime = 'text/xml'
		 	status = e.http_status
		 	resp = e.to_xml()
		 	headers = Headers()
			headers.add('Link', '<' + self.COMPLIANCE + '>;rel=profile')
			return Response(resp, status=status, mimetype=mime, headers=headers)

	def on_get_favicon(self, request):
		f = os.path.join(abs_path, 'favicon.ico')
		return Response(f, content_type='image/x-icon')
		

	def on_get_img_metadata(self, request, ident, format=None):
		## TODO:
		## Note that we can pickle response objects:
		## http://werkzeug.pocoo.org/docs/wrappers/#werkzeug.wrappers.Response
		## Would this be faster than reading from the FS?
		resp = None
		status = None
		mime = None
		headers = Headers()
		headers.add('Link', '<' + self.COMPLIANCE + '>;rel=profile')

		try:
			if format == 'json': 
				mime = 'text/json'
			elif format == 'xml': 
				mime = 'text/xml'
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
				raise PatokahException(404, ident, 'Identifier does not resolve to an image.')
			
			cache_dir = os.path.join(self.cache_root, ident)
			cache_path = os.path.join(cache_dir, 'info.') + format
			
			# check the cache
			if os.path.exists(cache_path):
				status = 200
				resp = file(cache_path)
				length = len(file(cache_path).read())
				logr.info('Read: ' + cache_path)
			else:
				status = 201 if self.use_201 else 200
				info = ImgInfo.fromJP2(img_path, ident)
				info.id = ident
				if format == 'xml':
					resp = info.toXML()
				else: # format == 'json':
					resp = info.toJSON()

				length = len(resp)

				# we could fork this off...
				if not os.path.exists(cache_dir): os.makedirs(cache_dir, 0755)

				logr.debug('made ' + cache_dir)

				f = open(cache_path, 'w')
				f.write(resp)
				f.close()
				logr.info('Created: ' + cache_path)

			headers.add('Content-Length', length)

		# except Exception as e:
		# 	raise PatokahException(500, '', e.message)
		except PatokahException as e:
		 	mime = 'text/xml'
		 	status = e.http_status
		 	resp = e.to_xml()

		finally:
			# TODO - caching headers 
			return Response(resp, status=status, mimetype=mime, headers=headers)

	def on_get_img(self, request, ident, region, size, rotation, quality, format=None):
		# TODO: 
		"""
		Get an image based on the *Parameter objects and values returned by the 
		converters.
		@param request: a werkzeug Request object
		@type request: Request

		@param ident: the image identifier
		@type ident: string

		@param region
		@type region: RegionParameter

		@param size
		@type size: SizeParameter

		@param rotation: rotation of the image (multiples of 90 for now)
		@type rotation: integer

		@param quality: 'native', 'color', 'grey', 'bitonal'
		@type quality: string

		@param format - 'jpg' or 'png'
		@type format: string
		"""
		try:
			resp = None
			status = None
			mime = None
			headers = Headers()
			headers.add('Link', '<' + self.COMPLIANCE + '>;rel=profile')

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

			if quality == 'bitonal':
				msg = 'Bitonal image requests are not supported by this server.'
				raise PatokahException(501, quality, msg)

			img_dir = os.path.join(self.cache_root, ident, region.url_value, size.url_value, rotation.url_value)
			img_path = os.path.join(img_dir, quality + '.' + format)
			logr.debug('img_dir: ' + img_dir)
			logr.debug('img_path: ' + img_path)

			# check the cache
			if os.path.exists(img_path):
				status = 200
				resp = file(img_path)
				length = len(file(img_path).read()) 
				headers.add('Content-Length', length) # do we want to bother?
				logr.info('Read: ' + img_path)
			else:
				status = 201 if self.use_201 else 200
				jp2 = self._resolve_identifier(ident)
				
				# We may not want to read this from the file every time, though 
				# it is pretty fast. Runtime cache? In memory dicts and Shelve/
				# pickle are not thread safe for writing (and probably wouldn't
				# scale anyway)
				# ZODB? : http://www.zodb.org/
				info = ImgInfo.fromJP2(jp2, ident)
				
				# Do this early to avoid even starting to build the shell outs
				try:
					region_kdu_arg = region.to_kdu_arg(info, self.cache_px_only)
					# This happens when cache_px_only=True; we re-call the 
					# method with a new RegionParameter object that is included
					# with the PctRegionException
				except PctRegionException as e:
					logr.info(e.msg)
					self.on_get_img(self, request, ident, e.new_region_param, size, rotation, quality, format)
					# Should only be raised if cache_px_only is set to True.

				# Build a script based on everything we know.
				os.makedirs(img_dir, 0755)
				logr.info('Made directory: ' + img_dir)

				# This could get a lot more sophisticated, e.g. use cjpeg for 
				# jpegs, jp2 levels for certain sizes, etc., different utils for
				# different formats, etc.

				# make a named pipe for the temporary bitmap
				fifo_path = os.path.join(self.tmp_dir, self.random_str(8) + '.bmp')
				mkfifo_call= self.mkfifo_cmd + ' ' + fifo_path
				try:
					logr.debug('Calling ' + mkfifo_call)
					subprocess.check_call(mkfifo_call, shell=True)
					logr.debug('Done (' + mkfifo_call + ')')

					# make and call the kdu_expand cmd
					kdu_expand_call = ''
					kdu_expand_call += self.kdu_expand_cmd + ' -quiet '
					kdu_expand_call += '-i ' + jp2 
					kdu_expand_call += ' -o ' + fifo_path
					kdu_expand_call += ' ' + region_kdu_arg
					
					# TODO: we need a way to catch errors here, but if we wait, it
					# hangs
					# try:
					logr.debug('Calling ' + kdu_expand_call)
					kdu_expand_proc = subprocess.Popen(kdu_expand_call, shell=True, bufsize=-1)
					# except CalledProcessError as cpe:
					# 	msg = cpe.cmd + ' exited with ' + cpe.returncode
					# 	logr.error(cpe.cmd + ' exited with ' + cpe.returncode)
					# 	raise PatokahException(500, '', msg)

					# make and call the convert command
					convert_call = ''
					convert_call = self.convert_cmd + ' '
					convert_call += fifo_path + ' '
					convert_call += size.to_convert_arg() + ' '
					convert_call += rotation.to_convert_arg() + ' '
					if format == 'jpg':
					 	convert_call += '-quality 90 '
					 	# TODO: more thought. For now, asking for a color image
					 	# gets you a color profile, where native will not. If 
					 	# the image is greyscale natively...this makes no sense.
					 	# Need data about the source image.
					 	if quality == 'color':
					 		convert_call += '-profile '
					 		convert_call += os.path.join(self.patoka_data_dir, 'sRGB.icc') + ' '
					if format == 'png':
						convert_call += '-quality 00 ' # This is tricky...

					if quality == 'grey':
						# see: http://www.imagemagick.org/Usage/color_mods/
						# convert_call += '-colorspace Gray '
						# TODO: this doesn't actually reduce the bit-depth (right?)
						convert_call += '-profile '
					 	convert_call += os.path.join(self.patoka_data_dir, 'gray22.icc') + ' '

					convert_call += img_path
				
					logr.debug('Calling ' + convert_call)
					subprocess.check_call(convert_call, shell=True, bufsize=-1)
					logr.debug('Done (' + convert_call + ')')
				
					kdu_expand_proc.terminate()
					logr.debug('Terminated ' + kdu_expand_call)

					logr.info("Created: " + img_path)

					resp = file(img_path)

				except CalledProcessError as cpe:
					msg = cpe.cmd + ' exited with ' + cpe.returncode
					logr.error(cpe.cmd + ' exited with ' + cpe.returncode)
					raise PatokahException(500, '', msg)

				# TODO: other exceptions

				finally:
					# make and call rm $fifo
					rm_fifo_call = self.rm_cmd + ' ' + fifo_path
					logr.debug('Calling ' + rm_fifo_call)
					subprocess.call(rm_fifo_call, shell=True)
					logr.debug('Done (' + rm_fifo_call + ')')

		# TODO: make sure all PatokahException subclasses bubble up to here:
		except PatokahException as e:
		 	mime = 'text/xml'
		 	status = e.http_status
		 	resp = e.to_xml()

		finally:
			# TODO - caching headers 
			return Response(resp, status=status, mimetype=mime, headers=headers)

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

	def to_kdu_arg(self, img_info, cache_px_only):
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
			# Re: above, Decimal is set to be precise to 32 places. float() was 
			# frequently off by 1
			if self.mode == 'pct' and cache_px_only:
				top_px = int(round(Decimal(self.y) * img_info.height / Decimal(100.0)))
				logr.debug('top_px: ' + str(top_px))
				left_px = int(round(Decimal(self.x) * img_info.width / Decimal(100.0)))
				logr.debug('left_px: ' + str(left_px))
				height_px = int(round(Decimal(self.h) * img_info.height / Decimal(100.0)))
				logr.debug('height_px: ' + str(height_px))
				width_px = int(round(Decimal(self.w) * img_info.width / Decimal(100.0)))
				logr.debug('width_px: ' + str(width_px))
				new_url_value = '%s,%s,%s,%s' % (left_px, top_px, width_px, height_px)
				new_region_param = RegionParameter(new_url_value)
				msg = '%s revised to %s' % (self.url_value, new_url_value)
				raise PctRegionException(new_region_param, msg)


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
			# to convert it means that it should be ignored
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
	# TODO: look at color info in the file and figure out qualities
	def __init__(self):
		self.id = id
		self.width = None
		self.height = None
		self.tile_width = None
		self.tile_height = None
		self.levels = None
	
	# Other fromXXX methods could be defined
	
	@staticmethod
	def fromJP2(path, img_id):
		info = ImgInfo()
		info.id = img_id

		"""
		Get the dimensions and levels of a JP2. There's enough going on here;
		make sure the file is available (exists and readable) before passing it.
		
		@see:  http://library.stanford.edu/iiif/image-api/#info
		"""
		jp2 = open(path, 'rb')
		jp2.read(2)
		b = jp2.read(1)
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) #skip over the SOC, 0x4F 
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x51: The SIZ marker segment
		if (ord(b) == 0x51):
			jp2.read(4) # get through Lsiz, Rsiz (16 bits each)
			info.width = int(struct.unpack(">HH", jp2.read(4))[1]) # Xsiz (32)
			info.height = int(struct.unpack(">HH", jp2.read(4))[1]) # Ysiz (32)
			logr.debug(path + " w: " + str(info.width))
			logr.debug(path + " h: " + str(info.height))
			jp2.read(8) # get through XOsiz , YOsiz  (32 bits each)
			info.tile_width = int(struct.unpack(">HH", jp2.read(4))[1]) # XTsiz (32)
			info.tile_height = int(struct.unpack(">HH", jp2.read(4))[1]) # YTsiz (32)
			logr.debug(path + " tw: " + str(info.tile_width))
			logr.debug(path + " th: " + str(info.tile_height))

		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x52: The COD marker segment
		if (ord(b) == 0x52):
			jp2.read(7) # through Lcod, Scod, SGcod (16 + 8 + 32 = 56 bits)
			info.levels = int(struct.unpack(">B", jp2.read(1))[0])
			logr.debug(path + " l: " + str(info.levels)) 
		jp2.close()
			
		return info
	
	def toXML(self):
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
		x += '  </formats>' + os.linesep
		x += '  <qualities>' + os.linesep
		x += '    <quality>native</quality>' + os.linesep
		x += '  </qualities>' + os.linesep
		x += '  <profile>http://library.stanford.edu/iiif/image-api/compliance.html#level1</profile>' + os.linesep
		x += '</info>' + os.linesep
		return x
	
	def toJSON(self):
		# cheaper!
		j = '{' + os.linesep
		j += '  "identifier" : "' + self.id + '",' + os.linesep
		j += '  "width" : ' + str(self.width) + ',' + os.linesep
		j += '  "height" : ' + str(self.height) + ',' + os.linesep
		j += '  "scale_factors" : [' + ", ".join(str(l) for l in range(1, self.levels+1)) + '],' + os.linesep
		j += '  "tile_width" : ' + str(self.tile_width) + ',' + os.linesep
		j += '  "tile_height" : ' + str(self.tile_height) + ',' + os.linesep
		j += '  "formats" : [ "jpg" ],' + os.linesep
		j += '  "qualities" : [ "native" ],' + os.linesep
		j += '  "profile" : "http://library.stanford.edu/iiif/image-api/compliance.html#level1"' + os.linesep
		j += '}' + os.linesep
		return j

# This seems easier than http://werkzeug.pocoo.org/docs/exceptions/ because we
# have this custom XML body.
class PatokahException(Exception):
	def __init__(self, http_status=404, supplied_value='', msg=''):
		"""
		"""
		super(PatokahException, self).__init__(msg)
		self.http_status = http_status
		self.supplied_value = supplied_value
		
	def to_xml(self):
		r = '<?xml version="1.0" encoding="UTF-8" ?>\n'
		r += '<error xmlns="http://library.stanford.edu/iiif/image-api/ns/">\n'
		r += '  <parameter>' + self.supplied_value  + '</parameter>\n'
		r += '  <text>' + self.message + '</text>\n'
		r += '</error>\n'
		return r

class BadRegionSyntaxException(PatokahException): pass
class BadRegionRequestException(PatokahException): pass
class BadSizeSyntaxException(PatokahException): pass
class BadSizeRequestException(PatokahException): pass
class BadRotationSyntaxException(PatokahException): pass
class FormatNotSupportedException(PatokahException): pass

class PctRegionException(Exception):
	"""To raise when regions are requested by percentage."""
	def __init__(self, new_region_param, msg):
		super(PctRegionException, self).__init__(msg)
		self.new_region_param = new_region_param
		

if __name__ == '__main__':
	'Run the development server'
	from werkzeug.serving import run_simple
	app = create_app(test=False)
	run_simple('127.0.0.1', 5004, app, use_debugger=True, use_reloader=True)
