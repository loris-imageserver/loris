# img.py
#-*-coding:utf-8-*-

from datetime import datetime
from logging import getLogger
from loris_exception import LorisException
from os import path,sep,symlink,makedirs,unlink
from parameters import RegionParameter
from parameters import RotationParameter
from parameters import SizeParameter
from loris_exception import RequestException
from loris_exception import SyntaxException
from loris_exception import ImageException
from urllib import unquote, quote_plus
from werkzeug.http import generate_etag
from urllib import unquote

logger = getLogger(__name__)

class ImageRequest(object):
	'''
	Slots:
		ident (str)
		region_value (str):
			copied exactly from the URI
		size_value (str)
			copied exactly from the URI
		rotation_value (str)
			copied exactly from the URI
		quality (str)
			copied exactly from the URI
		format (str)
			3 char string from the URI, (derived from) HTTP headers, or else the
			default.
		region_param (parameters.RegionParameter):
			See RegionParameter.__slots__. The region is represented there as
			both pixels and decmials.
		size_param (parameters.SizeParameter)
			See SizeParameter.__slots__.
		rotation_param (parameters.RotationParameter)
			See RotationParameter.__slots__.
		info (ImageInfo):
		is_canonical (bool):
			True if this is a canonical path.
		cache_path (str):
			Relative path from the cache root, based on the original request values.
		canonical_cache_path (str):
			Relative path from the cache root, based on normalized values
		request_path
			Path of the request for tacking on to the service host and creating
			a URI based on the original request.
		canonical_request_path
			Path of the request for tacking on to the service host and creating
			a URI based on the normalized ('canonical') values.
			('canonical') values.
		Raises:


	'''
	__slots__ = (
		'_canonical_cache_path',
		'_canonical_request_path',
		'_cache_path',
		'_info',
		'_is_canonical',
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
		self._canonical_cache_path = None
		self._canonical_request_path = None
		self._cache_path = None
		self._request_path = None

		self._is_canonical = None

		self._region_param = None
		self._rotation_param = None
		self._size_param = None

		# This is a little awkward. We may need it, but not right away (only if we're
		# filling out the param slots), so the user (of the class) has to set
		# it before accessing most of the above.
		self._info = None

	@property
	def region_param(self):
		if self._region_param is None:
			try:
				self._region_param = RegionParameter(self.region_value, self.info)
			except (SyntaxException,RequestException):
				raise
		return self._region_param

	@property
	def size_param(self):
		if self._size_param is None:
			try:
				self._size_param = SizeParameter(self.size_value, self.region_param)
			except (RequestException,SyntaxException):
				raise
		return self._size_param

	@property
	def rotation_param(self):
		if self._rotation_param is None:
			try:
				self._rotation_param = RotationParameter(self.rotation_value)
			except (RotationParameter,SyntaxException):
				raise
		return self._rotation_param

	@property
	def request_path(self):
		if self._request_path is None:
			p = '/'.join((
				quote_plus(self.ident),
				self.region_value,
				self.size_value,
				self.rotation_value,
				self.quality
			))
			self._request_path = '%s.%s' % (p,self.format)
		return self._request_path

	@property
	def canonical_request_path(self):
		if self._canonical_request_path is None:
			p = '/'.join((quote_plus(self.ident),
				self.region_param.canonical_uri_value,
				self.size_param.canonical_uri_value,
				self.rotation_param.canonical_uri_value,
				self.quality
			))
			self._canonical_request_path = '%s.%s' % (p,self.format)
		return self._canonical_request_path

	@property
	def cache_path(self):
		if self._cache_path is None:
			p = path.join(self.ident,
				self.region_value,
				self.size_value,
				self.rotation_value,
				self.quality
			)
			self._cache_path = '%s.%s' % (p, self.format)
		return self._cache_path

	@property
	def canonical_cache_path(self):
		if self._canonical_cache_path is None:
			p = path.join(self.ident,
					self.region_param.canonical_uri_value,
					self.size_param.canonical_uri_value,
					self.rotation_param.canonical_uri_value,
					self.quality
				)
			self._canonical_cache_path = '%s.%s' % (p, self.format)
		return self._canonical_cache_path

	@property
	def is_canonical(self):
		if self._is_canonical is None:
			self._is_canonical = self.cache_path == self.canonical_cache_path
		return self._is_canonical

	@property
	def info(self):
		if self._info is None:
			# For dev purposes only. This should never happen.
			raise ImageException(http_status=500, message='Image.info not set!')
		else:
			return self._info

	@info.setter
	def info(self, i):
		self._info = i

class ImageCache(dict):
	'''
	'''
	def __init__(self, cache_root):
		self.cache_root = cache_root

	def __contains__(self, image_request):
		return path.exists(self.get_cache_path(image_request))

	def __getitem__(self, image_request):
		fp = self.get(image_request)
		if fp is None:
			raise KeyError
		return fp

	@staticmethod
	def _link(to,frum):
		# under certain circumstances, files are generating circular
		# symlinks; don't do that
		if to == frum:
			logger.warn('Circular symlink requested from %s to %s; not creating symlink' % (frum, to))
			return
		link_dp = path.dirname(frum)
		if not path.exists(link_dp):
			makedirs(link_dp)
		if path.lexists(frum): # shouldn't be the case, but helps debugging
			unlink(frum)
		symlink(to,frum)
		logger.debug('Made symlink from %s to %s' % (to,frum))

	def __setitem__(self, image_request, fp):
		# The Image (fp) already exists, this simply makes a symlink in the
		# cache to from the canonical syntax to the actual request path
		if not image_request.is_canonical:
			canonical_fp = self.get_canonical_cache_path(image_request)
			ImageCache._link(fp, canonical_fp)

	def __delitem__(self, image_request):
		# if we ever decide to start cleaning our own cache...
		pass

	def get(self, image_request):
		'''Returns (str, ):
			The path to the file or None if the file does not exist.
		'''
		cache_fp = self.get_cache_path(image_request)
		last_mod = datetime.utcfromtimestamp(path.getmtime(cache_fp))
		if path.exists(cache_fp):
			return (cache_fp, last_mod)
		else:
			return None

	def get_cache_path(self, image_request):
		return path.realpath(path.join(self.cache_root, unquote(image_request.cache_path)))

	def get_canonical_cache_path(self, image_request):
		return path.realpath(path.join(self.cache_root, unquote(image_request.canonical_cache_path)))
