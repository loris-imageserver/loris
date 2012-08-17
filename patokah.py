# -*- coding: utf-8 -*-

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
			dispatch_to_method = ''
			 
			if self.test: dispatch_to_method = 'test_' + endpoint 
			else: dispatch_to_method = 'on_' + endpoint
			
			logr.debug('Dispatching to ' + dispatch_to_method)
			return getattr(self, dispatch_to_method)(request, **values)
		except NotFound, e:
			return self.error_404(e.description)
		except HTTPException, e:
			return e

	def on_get_img_metadata(self, request, ident, extension):
		# TODO: all of these MIMEs should be constants, and probably support application/* as well
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
			resp = file(cache_path)
		else:
			info = ImgInfo.fromJP2(img_path)
			info.id = ident
			if mime == 'text/xml':
				resp = info.toXML()
			else:
				resp = info.toJSON()
			
			# we could fork this off...
			if not os.path.exists(cache_dir): os.makedirs(cache_dir, 0755)
			logr.debug('made ' + cache_dir)
			f = open(cache_path, 'w')
			f.write(resp)
			f.close()
			logr.info('Created: ' + cache_path)
			
		return Response(resp, mimetype=mime,)
	
	# Do we want: http://docs.python.org/library/queue.html ?


	def test_get_img(self, request, ident, region, size, rotation, quality, format):
		"""
		Helper for our testConverters unit test. The response is a dictionary of 
		dictionaries that are returned from our converters' to_python methods.
		"""
		r = {}
		r['region'] = region
		r['size'] = size
		r['rotation'] = rotation
		return Response(str(r))

	def on_get_img(self, request, ident, region, size, rotation, quality, format):
		# TODO: 
		"""
		Get an image based on the values or dictionaries returned by our 
		converters.
		"""
		
		if format == 'jpg':
			mime = 'image/jpeg'
			ext = format
			
		if format == 'png':
			mime = 'image/png'
			ext = format
		
		jp2 = self._resolve_identifier(ident)
		
		# TODO: we probably don't want to read this from the file every time.
		# Runtime cache? db?
		info = ImgInfo.fromJP2(jp2)
		
		out_dir = os.path.join(self.CACHE_ROOT, ident, region, size, rotation)
		out = os.path.join(out_dir, quality) + '.' + ext
		
		# 8/16/2012: start here, nothing below this is actual implementation.
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
		self.logr.info("Made file: " + out)
	
		rm_cmd = self.RM + " " + fifopath
		logr.debug(rm_cmd)
		rm_proc = subprocess.Popen(rm_cmd, shell=True)
		
		return out

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
		return params

	def to_url(self, value):
		return RegionParameter(value)

class RegionParameter(object):
	"""
	self.mode is always one of 'full', 'pct', or 'pixel'
	"""
	def __init__(self, url_value):
		self.url_value = url_value
		self.mode = ''
		self.x, self.y, self.w, self.y = [None, None, None, None]

		if self.url_value == 'full':
			self.mode = 'full'
		else:
			try:
				if url_value.split(':')[0] == 'pct':
					self.mode = 'pct'
					pct_value = url_value.split(':')[1]
					logr.debug('Percent dimensions request: ' + pct_value)
					# floats!
					dimensions = [float(d) for d in pct_value.split(',')]
					if any(n > 100.0 for n in dimensions):
						msg = 'Percentages must be less than 100.0.'
						raise BadRegionSyntaxException(400, url_value, msg)
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, url_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
				else:
					self.mode = 'pixel'
					logr.debug('Pixel dimensions request: ' + url_value)
					# ints only!
					dimensions = [int(d) for d in url_value.split(',')]
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, url_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
			except Exception, e :
				msg = 'Region syntax not valid. ' + e.message
				raise BadRegionSyntaxException(400, url_value, msg)

	def to_kdu_arg(self, img_info):
		pass
		

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
		params = {}.fromkeys(('is_full', 'force_aspect', 'value', 'w', 'h', 'pct'))
		params['value'] = value
		try:
			if value == 'full':
				params['is_full'] = True
			elif value.startswith('pct:'):
				try:
					pct = int(value.split(':')[1])
					if pct > 100:
						raise Exception('Percentage supplied is greater than 100. Upsampling is not supported.')
					else:
						params['pct'] = pct
				except:
					raise
			elif value.endswith(','):
				try:
					params['w'] = int(value[:-1])
				except:
					raise
			elif value.startswith(','):
				try:
					params['h'] = int(value[1:])
				except:
					raise
			elif value.startswith('!'):
				params['force_aspect'] = False
				try:
					params['w'], params['h'] = (int(d) for d in value[1:].split(','))
				except:
					raise
			else:
				params['force_aspect'] = True
				try:
					params['w'], params['h'] = (int(d) for d in value.split(','))
				except:
					raise
		except ValueError, e:
			msg = 'Bad size syntax. '
			msg += 'Check that the supplied width and/or height or\n'
			msg += 'percentage are integers, and that a comma (",") is '
			msg += 'used as the w,h separator. \nOriginal error message: '
			raise BadSizeSyntaxException(400, value,  msg + e.message)
		except Exception, e:
			raise BadSizeSyntaxException(400, value, 'Bad size syntax. ' + e.message)
		
		if any((dim < 1 and dim != None) for dim in (params['w'], params['h'])):
			raise BadSizeSyntaxException(400, value, 'Width and height must both be positive numbers')
		
		if params['is_full'] == None: params['is_full'] = False
		
		return params

	def to_url(self, value):
		return str(value) # ??

class RotationConverter(BaseConverter):
	"""
	Custom converter for the rotation paramater.
	
	@see http://library.stanford.edu/iiif/image-api/#rotation
	
	@return: the nearest multiple of 90 as an int
	
	"""
	def __init__(self, url_map):
		super(RotationConverter, self).__init__(url_map)
		self.regex = '\-?\d+'

	def to_python(self, value):
		# Round. kdu can handle negatives values > 360 and < -360
		nearest90 = int(90 * round(float(value) / 90)) 
		return nearest90

	def to_url(self, value):
		return str(value)

class ImgInfo(object):
	# TODO: look at color info in the file and figure out qualities
	def __init__(self):
		self.id = None
		self.width = None
		self.height = None
		self.tile_width = None
		self.tile_height = None
		self.levels = None
	
	# other fromXXX methods can be defined, you see...
	
	@staticmethod
	def fromJP2(path):
		info = ImgInfo()
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
		for s in range(1, self.levels):
			x += '	<scale_factor>' + str(s) + '</scale_factor>' + os.linesep
		x += '  </scale_factors>' + os.linesep
		x += '  <tile_width>' + str(self.tile_width) + '</tile_width>' + os.linesep
		x += '  <tile_height>' + str(self.tile_height) + '</tile_height>' + os.linesep
		x += '  <formats>' + os.linesep
		x += '	<format>jpg</format>' + os.linesep
		x += '  </formats>' + os.linesep
		x += '  <qualities>' + os.linesep
		x += '	<quality>native</quality>' + os.linesep
		x += '  </qualities>' + os.linesep
		x += '</info>' + os.linesep
		return x
	
	def toJSON(self):
		# cheaper!
		j = '{' + os.linesep
		j += '  "identifier" : "' + self.id + '",' + os.linesep
		j += '  "width" : ' + str(self.width) + ',' + os.linesep
		j += '  "height" : ' + str(self.height) + ',' + os.linesep
		j += '  "scale_factors" : [' + ", ".join(str(l) for l in range(1, self.levels)) + '],' + os.linesep
		j += '  "tile_width" : ' + str(self.tile_width) + ',' + os.linesep
		j += '  "tile_height" : ' + str(self.tile_height) + ',' + os.linesep
		j += '  "formats" : [ "jpg" ],' + os.linesep
		j += '  "quality" : [ "native" ]' + os.linesep
		j += '}'
		return j

class ConverterException(Exception):
	def __init__(self, http_status=404, supplied_value='', msg=''):
		"""
		"""
		super(ConverterException, self).__init__(msg)
		self.http_status = http_status
		self.supplied_value = supplied_value
		
	def to_xml(self):
		pass
	
class BadRegionSyntaxException(ConverterException): pass
class BadSizeSyntaxException(ConverterException): pass


if __name__ == '__main__':
	'Run the development server'
	from werkzeug.serving import run_simple
	app = create_app(test=False)
	run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
