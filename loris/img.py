# img.py
#-*-coding:utf-8-*-

from log_config import get_logger
from loris_exception import LorisException
from os import path,sep
from parameters import RegionParameter
from parameters import RegionRequestException
from parameters import RegionSyntaxException
from parameters import RotationParameter
from parameters import RotationSyntaxException
from parameters import SizeParameter
from parameters import SizeRequestException
from parameters import SizeSyntaxException
from urllib import unquote, quote_plus
from werkzeug.http import generate_etag

logger = get_logger(__name__)

class Image(object):
	'''
	Everything we need to know about an image.

	Slots:
		ident
		region_value
		size_value
		rotation_value
		quality
		format
		region_param
		size_param
		rotation_param
		info (ImageInfo):
		is_cannonical (bool):
			True if this is a cannonical path.
		cache_path (str): 
			Relative path from the cache root, based on the original request values.
		c14n_cache_path (str):
			Relative path from the cache root, based on normalized values
		request_path
			Path of the request for tacking on to the service host and creating 
			a URI based on the original request.
		c14n_request_path
			Path of the request for tacking on to the service host and creating 
			a URI based on the normalized ('cannonical') values.
			('cannonical') values.

	'''
	__slots__ = (
		'_c14n_cache_path',
		'_c14n_request_path',
		# 'c14n_request_path',
		'_cache_path',
		'_etag',
		'_info',
		'_is_cannonical',
		# 'is_cannonical',
		'_region_param',
		'_request_path',
		'_rotation_param',
		'_size_param',
		'format',
		'ident',
		'quality',
		'region_value',
		'rotation_value',
		'size_value'
	)

	def __init__(self, ident, region, size, rotation, quality, target_format):

		self.ident, self.region_value, self.size_value = map(unquote, (ident, region, size))
		self.rotation_value = rotation
		self.quality = quality
		self.format = target_format

		logger.debug('region slice: %s' % (str(region),))
		logger.debug('size slice: %s' % (str(size),))
		logger.debug('rotation slice: %s' % (str(rotation),))
		logger.debug('quality slice: %s' % (self.quality,))
		logger.debug('format extension: %s' % (self.format,))

		# These aren't set until we first access them
		self._c14n_cache_path = None
		self._c14n_request_path = None
		self._cache_path = None
		self._request_path = None

		self._etag = None

		self._is_cannonical = None

		self._region_param = None
		self._rotation_param = None
		self._size_param = None

		# This is awkward. We may need it, but not right away, so the user (of 
		# the class) has to set it before accessing most of the above. An 
		self._info = None



	@property
	def region_param(self):
		if self._region_param is None:
			try:
				self._region_param = RegionParameter(self.region_value, self.info)
			except (RegionSyntaxException,RegionRequestException):
				raise
		return self._region_param

	@property
	def size_param(self):
		if self._size_param is None:
			try:
				self._size_param = SizeParameter(self.size_value, self.region_param)
			except (SizeRequestException,SizeSyntaxException):
				raise
		return self._size_param

	@property
	def rotation_param(self):
		if self._rotation_param is None:
			try:
				self._rotation_param = RotationParameter(self.rotation_value)
			except (RotationParameter,RotationSyntaxException):
				raise
		return self._rotation_param

	@property
	def request_path(self):
		if self._request_path is None:
			escaped_ident = quote_plus(self.ident)
			p = '/'.join((escaped_ident, self.region_value, self.size_value, self.rotation_value, self.quality))
			self._request_path = '%s.%s' % (p,self.format)
		return self._request_path

	@property
	def c14n_request_path(self):
		if self._c14n_request_path is None:
			p = '/'.join((self.ident, 
				self.region_param.cannonical_uri_value, 
				self.size_param.cannonical_uri_value, 
				self.rotation_param.cannonical_uri_value, 
				self.quality
			))
			self._c14n_request_path = '%s.%s' % (p,self.format)
		return self._c14n_request_path

	@property
	def cache_path(self):
		if self._cache_path is None:
			p = path.join(self.ident, self.region_value, self.size_value, self.rotation_value, self.quality)
			self._cache_path = '%s.%s' % (p,self.format)
		return self._cache_path

	@property
	def c14n_cache_path(self):
		if self._c14n_cache_path is None:
			p = path.join(self.ident, 
					self.region_param.cannonical_uri_value, 
					self.size_param.cannonical_uri_value, 
					self.rotation_param.cannonical_uri_value, 
					self.quality
				)
			self._c14n_cache_path = '%s.%s' % (p,self.format)
		return self._c14n_cache_path


	@property
	def is_cannonical(self):
		if self._is_cannonical is None:
			self._is_cannonical = self.cache_path == self.c14n_cache_path
		return self._is_cannonical

	@property
	def etag(self):
		if self._etag is None:
			# TODO: see if this works, otherwise use the file (which is bigger)
			self._etag = generate_etag(self.info) 
		return self._etag

	@property
	def info(self):
		if self._info is None:
			raise ImageException(http_status=500, message='Image.info not set!')
		else:
			return self._info

	@info.setter
	def info(self, i):
		self._info = i

class ImageCache(object):
	'''
	'''
	def __init__(self, root):
		self.__root = root

	def __contains__(self, image):
		pass

	def __getitem__(self, image):
		# TODO: if we want this to look like a real dict, should raise a 
		# KeyError if the file doesn't exist.
		self.get(image)

	def __setitem__(self, image): # does this make sense?
		self.put(image)

	def __delitem__(self, image):
		pass

	def get(self, image):
		# remember that the path may be a symlink.
		pass

	def put(self, image):
		'''
		Args:
			image (Image)			
		'''
		pass



class ImageException(LorisException): pass


