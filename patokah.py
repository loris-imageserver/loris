# -*- coding: utf-8 -*-

from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
import ConfigParser
import logging
import logging.config
import os
import struct
import urlparse
import werkzeug

_LIB = os.path.join(os.path.dirname(__file__), 'lib')
_BIN = os.path.join(os.path.dirname(__file__), 'bin')
_ETC = os.path.join(os.path.dirname(__file__), 'etc')
_ENV = {"LD_LIBRARY_PATH":_LIB, "PATH":_LIB + ":$PATH"}

conf_file = os.path.join(_ETC, 'patokah.conf')
logging.config.fileConfig(conf_file)
logr = logging.getLogger('patokah')
logr.info("Logging initialized")

def create_app(test=False):
	app = Patokah(test)
	return app

# Note when we start to stream big files from the filesystem, see:
# http://stackoverflow.com/questions/5166129/how-do-i-stream-a-file-using-werkzeug

# TODO: do we need a format converter? Would like to support png as well.

class Patokah(object):
	def __init__(self, test=False):
		"""
		@param test: changes our dispatch methods. 
		"""
		
		# Configuration - Everything else
		_conf = ConfigParser.RawConfigParser()
		_conf.read(conf_file)

		self.test=test

		self.CJPEG = _conf.get('utilities', 'cjpeg')
		self.MKFIFO = _conf.get('utilities', 'mkfifo')
		self.RM = _conf.get('utilities', 'rm')
		
		self.TMP_DIR = _conf.get('directories', 'tmp')
		
		# TODO: need a cache test
		self.CACHE_ROOT = _conf.get('directories', 'cache_root')

		self.COMPLIANCE = _conf.get('compliance', 'uri')
		
		self.SRC_IMAGES_ROOT = ""
		if self.test:
			self.SRC_IMAGES_ROOT = os.path.join(os.path.dirname(__file__), 'test_img') 
		else:
			self.SRC_IMAGES_ROOT = _conf.get('directories', 'src_img_root')
		
		for d in (self.TMP_DIR, self.CACHE_ROOT):
			if not os.path.exists(d):
				os.makedirs(d, 0755)
				logr.info("Created " + d)

		converters = {
				'region' : RegionConverter,
				'size' : SizeConverter,
				'rotation' : RotationConverter
			}
		self.url_map = Map([
			Rule('/<path:ident>/info.<any(json, xml):extension>', endpoint='get_img_metadata'),
			Rule('/<path:ident>/<region:region>/<size:size>/<rotation:rotation>/<any(native, color, grey, bitonal):quality>.<format>', endpoint='get_img')
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
			
			logr.debug('Dispatching to ' + dispatch_to_method)
			return getattr(self, dispatch_to_method)(request, **values)
		except NotFound, e:
			return self.error_404(e.description)
		except HTTPException, e:
			return e

	def on_get_img_metadata(self, request, ident, extension):
		## TODO:
		## Note that we can pickle response objects:
		## http://werkzeug.pocoo.org/docs/wrappers/#werkzeug.wrappers.Response
		## Would this be faster than reading from the FS?

		mime = None
		resp_code = None
		if extension == 'json': 
			mime = 'text/json'
		elif extension == 'xml': 
			mime = 'text/xml'
		else:
			pass
			# TODO: raise (406 or something like that...format not supported)
			
		img_path = self._resolve_identifier(ident)
		
		if not os.path.exists(img_path):
			raise NotFound('"' + ident + '" does not resolve to an image.')
		
		
		cache_dir = os.path.join(self.CACHE_ROOT, ident)
		cache_path = os.path.join(cache_dir, 'info.') + extension
		
		# check the cache
		if os.path.exists(cache_path):
			status = 200
			resp = file(cache_path)
			length = len(file(cache_path).read())
			logr.info('Read: ' + cache_path)
		else:
			status = 201
			info = ImgInfo.fromJP2(img_path, ident)
			info.id = ident
			if mime == 'text/xml':
				resp = info.toXML()
			else:
				resp = info.toJSON()

			length = len(resp)

			# we could fork this off...
			if not os.path.exists(cache_dir): os.makedirs(cache_dir, 0755)

			logr.debug('made ' + cache_dir)

			f = open(cache_path, 'w')
			f.write(resp)
			f.close()
			logr.info('Created: ' + cache_path)
		
		headers = Headers()
		headers.add('Link', '<' + self.COMPLIANCE + '>;rel=profile')
		headers.add('Content-Length', length)
		r = Response(resp, status=status, mimetype=mime, headers=headers)
		
		# return Response(resp, status=status, mimetype=mime, headers=headers)
		return r
	
	# Do we want: http://docs.python.org/library/queue.html ?

	# TODO: below needs a test and needs to be used wherever we raise
	def err_to_xml(self, param, text):
		r = '<?xml version="1.0" encoding="UTF-8" ?>\n'
		r += '<error xmlns="http://library.stanford.edu/iiif/image-api/ns/">\n'
		r += '  <parameter>' + param + '</parameter>\n'
		r += '  <text>' + text + '</text>\n'
		r += '</error>\n'
		return r

	def on_get_img(self, request, ident, region, size, rotation, quality, format):
		# TODO: 
		"""
		Get an image based on the *Parameter objects and values returned by our 
		converters.

		@param ident: the image identifier
		@type ident: string

		@param region
		@type region: RegionParameter

		@param size
		@type size: SizeParameter

		@param rotation: rotation of the image, multiples of 90 for now
		@type rotation: integer

		@param quality: 'native', 'color', 'grey', 'bitonal'
		@type quality: string

		@param format - 'jpg' or 'png' (for now)
		@type format: string
		"""
		# This method should always return a Response.
		
		#TODO: ulitmately wrap this is try/catches. Most exceptions/messages
		# will come from raises by the converters, but we may have to add a few
		# more 4xx responses based on image dimensions. 
		
		if format == 'jpg':
			mime = 'image/jpeg'
			ext = format
			
		if format == 'png':
			mime = 'image/png'
			ext = format
		
		jp2 = self._resolve_identifier(ident)
		
		# TODO: we probably don't want to read this from the file every time.
		# Runtime cache? db? Python dictionaries are not thread-safe for 
		# writing.
		info = ImgInfo.fromJP2(jp2)
		
		out_dir = os.path.join(self.CACHE_ROOT, ident, region, size, rotation)
		out = os.path.join(out_dir, quality) + '.' + ext
		
		# 8/27/2012: start here, 
		# * Implement to_kdu_arg() methods
		# * Write to_kdu_arg() tests
		# * Build comm
		#nothing below this is actual implementation.
		# approach: make functions that take an ImgInfo object and one of the
		# dictionaries returned from the converters and build the appropriate
		# part of the shellout.
		  
		
		# Use a named pipe to give kdu and cjpeg format info.
		fifopath = os.path.join(self.TMP_DIR, rand_str() + '.bmp')
		mkfifo_cmd = self.MKFIFO + " " + fifopath
		logr.debug(mkfifo_cmd) 
		mkfifo_proc = subprocess.Popen(mkfifo_cmd, shell=True)
		mkfifo_proc.wait()
		
		# Build the kdu_expand call
		kdu_cmd = KDU_EXPAND + " -i " + jp2 
		if region != 'full': kdu_cmd = kdu_cmd + " -region " + region
		if rotation != 0:  kdu_cmd = kdu_cmd + " -rotate " + rotation
		kdu_cmd = kdu_cmd + " -o " + fifopath
		logr.debug(kdu_cmd)
		kdu_proc = subprocess.Popen(kdu_cmd, env=_ENV, shell=True)
	
		# What are the implications of not being able to wait here (not sure why
		# we can't, but it hangs when we try). I *think* that as long as there's 
		# data flowing into the pipe when the next process (below) starts we're 
		# just fine.
		
		# TODO: if format is not jpg, [do something] (see spec)
		# TODO: quality, probably in the recipe below
		
		if not os.path.exists(out_dir):
			os.makedirs(out_dir, 0755)
			self.logr.info("Made directory: " + out_dir)
		cjpeg_cmd = self.CJPEG + " -outfile " + out + " " + fifopath 
		logr.debug(cjpeg_cmd)
		cjpeg_proc = subprocess.call(cjpeg_cmd, shell=True)
		self.logr.info("Read: " + out)
	
		rm_cmd = self.RM + " " + fifopath
		logr.debug(rm_cmd)
		rm_proc = subprocess.Popen(rm_cmd, shell=True)

		# TODO: needs unit test
		if not os.path.exists(jp2):
			
			msg = 'Image specified by this identifier does not exist.'
			logr.error(msg + ': ' + ident)
			r = self.err_to_xml(ident, msg)
			return Response(r,status=404,mimetype='text/xml')
			
		
		# TODO: we probably don't want to read this from the file every time.
		# Runtime cache? db? in memory dicts and Shelve/pickle are not thread 
		# safe for writing.
		# ZODB? : http://www.zodb.org/
		info = ImgInfo.fromJP2(jp2)
		
		out_dir = os.path.join(self.CACHE_ROOT, ident, str(region['value']), str(size['value']), str(rotation))
		# hold off making the above dir until we succeed??
		out_path = os.path.join(out_dir, quality) + '.' + ext
		
		logr.debug('output path: ' + out_path)
		
		headers = Headers()
		headers.add('Link', '<' + self.COMPLIANCE + '>;rel=profile')
		# TODO: Content-Length

		return Response(out_path, mimetype=mime, headers=headers)


#		# Use a named pipe to give kdu and cjpeg format info.
#		fifopath = os.path.join(self.TMP_DIR, rand_str() + _BMP)
#		mkfifo_cmd = self.MKFIFO + " " + fifopath
#		logr.debug(mkfifo_cmd) 
#		mkfifo_proc = subprocess.Popen(mkfifo_cmd, shell=True)
#		mkfifo_proc.wait()
#		
#		# Build the kdu_expand call - this should be in a function that takes 
#		#the image info plus the region, size, rotation
#		kdu_cmd = KDU_EXPAND + " -i " + jp2 
#		if region != 'full': kdu_cmd = kdu_cmd + " -region " + region
#		if rotation != 0:  kdu_cmd = kdu_cmd + " -rotate " + rotation
#		kdu_cmd = kdu_cmd + " -o " + fifopath
#		logr.debug(kdu_cmd)
#		kdu_proc = subprocess.Popen(kdu_cmd, env=_ENV, shell=True)
#	
#		# What are the implications of not being able to wait here (not sure why
#		# we can't, but it hangs when we try). I *think* that as long as there's 
#		# data flowing into the pipe when the next process (below) starts we're 
#		# just fine.
#		
#		# TODO: if format is not jpg, [do something] (see spec)
#		# TODO: quality, probably in the recipe below
#		
#		if not os.path.exists(out_dir):
#			os.makedirs(out_dir, 0755)
#			self.logr.info("Made directory: " + out_dir)
#		cjpeg_cmd = self.CJPEG + " -outfile " + out + " " + fifopath 
#		logr.debug(cjpeg_cmd)
#		cjpeg_proc = subprocess.call(cjpeg_cmd, shell=True)
#		self.logr.info("Made file: " + out)
#	
#		rm_cmd = self.RM + " " + fifopath
#		logr.debug(rm_cmd)
#		rm_proc = subprocess.Popen(rm_cmd, shell=True)
#		
#		return out

	# static?
	def _resolve_identifier(self, ident):
		"""
		Given the identifier of an image, resolve it to an actual path. This
		would need to be overridden to suit different environments.
		
		This simple version just prepends a constant path to the identfier
		supplied, and appends a file extension, resulting in an absolute path 
		on the filesystem.
		"""
		return os.path.join(self.SRC_IMAGES_ROOT, ident + '.jp2')

	#TODO: http://library.stanford.edu/iiif/image-api/#errors
	def error_404(self, message):
		response = Response(message, mimetype='text/plain')
		response.status_code = 404
		return response

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
					if any((n > 100.0 or n <= 0) for n in dimensions):
						msg = 'Percentages must be between 0 and 100.'
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
		# width and height
		#if any(dim < 1 for )
		cmd = ''
		if self.mode != 'full':
			cmd = '-region '

			# First: convert into decimals (we'll pass these to kdu after)
			# we test them

			top = self.y / 100.0 if self.mode == 'pct' else float(self.y) / img_info.height
			left = self.x / 100.0 if self.mode == 'pct' else float(self.x) / img_info.width
			height = self.h / 100.0 if self.mode == 'pct' else float(self.h) / img_info.height
			width = self.w / 100.0 if self.mode == 'pct' else float(self.w) / img_info.width
			
			# THESE CONVERSIONS CAN LEAVE US OFF BY A PIXEL.... 
			# try 0,0,1358,1800. Result is 1359 wide.
			# What to do?
			# 

			# "If the request specifies a region which extends beyond the 
			# dimensions of the source image, then the service should return an 
			# image cropped at the boundary of the source image."
			if (width + left) > 1.0: 
				width = 1.0 - left
				logr.debug('Width adjusted to %s' % width)
			if (top + height) > 1.0: 
				height = 1.0 - top
				logr.debug('Height adjusted to %s' % height)
			# Catch OOB errors:
			# top and left
			if any(axis < 0 for axis in (top, left)):
				msg = 'x and y region paramaters must be 0 or greater'
				raise BadRegionRequestException(400, self.url_value, msg)
			if left >= 1.0:
				msg = 'Region x parameter is out of bounds.\n'
				msg += self.x + ' was supplied and image width is ' 
				msg += img_info.width
				raise BadRegionRequestException(400, self.url_value, msg)
			if top >= 1.0:
				msg = 'Region y parameter is out of bounds.\n'
				msg += self.y + ' was supplied and image height is ' 
				msg += img_info.height
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
		
	def to_kdu_arg(self, img_info):
		pass

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

	def to_kdu_arg(self):
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

class PatokahException(Exception):
	def __init__(self, http_status=404, supplied_value='', msg=''):
		"""
		"""
		super(PatokahException, self).__init__(msg)
		self.http_status = http_status
		self.supplied_value = supplied_value
		
	def to_xml(self):
		pass
	
class BadRegionSyntaxException(PatokahException): pass
class BadRegionRequestException(PatokahException): pass
class BadSizeSyntaxException(PatokahException): pass
class BadRotationSyntaxException(PatokahException): pass

if __name__ == '__main__':
	'Run the development server'
	from werkzeug.serving import run_simple
	app = create_app(test=False)
	run_simple('127.0.0.1', 5003, app, use_debugger=True, use_reloader=True)
