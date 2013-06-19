# img_info.py

from PIL import Image
from collections import OrderedDict
from collections import deque
from constants import IMG_API_NS, COMPLIANCE
from datetime import datetime
from log_config import get_logger
from threading import Lock
import fnmatch
import json
import loris_exception
import os
import struct

logger = get_logger(__name__)

# TODO: we may want a little more exception handling in here.

STAR_DOT_JSON = '*.json'

PIL_MODES_TO_QUALITIES = {
	# Thanks to http://stackoverflow.com/a/1996609/714478
	'1' : ['native','bitonal'],
	'L' : ['native','grey','bitonal'],
	'P' : ['native','grey','bitonal'],
	'RGB': ['native','color','grey','bitonal'],
	'RGBA': ['native','color','grey','bitonal'],
	'CMYK': ['native','color','grey','bitonal'],
	'YCbCr': ['native','color','grey','bitonal'],
	'I': ['native','color','grey','bitonal'],
	'F': ['native','color','grey','bitonal']
}

class ImageInfo(object):
	'''Info about the image.

	See: <http://www-sul.stanford.edu/iiif/image-api/#info>

	Slots:
		ident (str): The image identifier.
		width (int)
		height (int)
		tile_width (int)
		tile_height (int)
		scale_factors [(int)]
		qualities [(str)]: 'native', 'bitonal', 'color', or 'grey'
		__native_quality: 'color' or 'grey'
		src_format (str): as a three char file extension 
		src_img_fp (str): the absolute path on the file system
	'''
	__slots__ = ('scale_factors', 'width', 'tile_height', 'height', 
		'__native_quality', 'tile_width', 'qualities', 'formats', 'ident', 
		'src_format', 'src_img_fp')

	@staticmethod
	def from_image_file(ident, uri, src_img_fp, src_format, formats=[]):
		'''
		Args:
			ident (str): The URI for the image.
			src_img_fp (str): The absolute path to the image.
			src_format (str): The format of the image as a three-char str.
			formats ([str]): The derivative formats the application can produce.
		'''
		# We're going to assume the image exists and the format is supported.
		# Exceptions should be raised by the resolver if that's not the case.
		new_inst = ImageInfo()
		new_inst.ident = uri
		new_inst.src_img_fp = src_img_fp
		new_inst.src_format = src_format
		new_inst.tile_width = None
		new_inst.tile_height = None
		new_inst.scale_factors = None
		new_inst.formats = formats

		logger.debug('Source Format: %s' % (new_inst.src_format,))
		logger.debug('Source File Path: %s' % (new_inst.src_img_fp,))
		logger.debug('Identifier: %s' % (new_inst.ident,))

		if new_inst.src_format == 'jp2':
			new_inst.__from_jp2(src_img_fp)
		elif new_inst.src_format == 'jpg':
			new_inst.__from_jpg(src_img_fp)
		elif new_inst.src_format == 'tif':
			new_inst.__from_tif(src_img_fp)
		else:
			raise Exception('Didn\'t get a source format, or at least one we recognize')

		return new_inst


	@staticmethod
	def from_json(path):
		"""Contruct an instance from an existing file.

		Args:
			path (str): the path to a JSON file.

		Raises:
			Exception
		"""
		new_inst = ImageInfo()
		# try:
		f = open(path, 'r')
		j = json.load(f)
		new_inst.ident = j.get(u'@id')
		new_inst.width = j.get(u'width')
		new_inst.height = j.get(u'height')
		# TODO: make sure these are resulting in error or Nones/nulls when 
		# we load from the filesystem
		new_inst.scale_factors = j.get(u'scale_factors')
		new_inst.tile_width = j.get(u'tile_width')
		new_inst.tile_height = j.get(u'tile_height')
		new_inst.formats = j.get(u'formats')
		new_inst.qualities = j.get(u'qualities')
		# except Exception as e: # TODO: be more specific...
		# 	iie = ImageInfoException(500, str(e))
		# 	raise iie
		# finally:
		f.close()
		return new_inst

	def __from_jpg(self, fp):
		# This is cheap, and presumably we're pulling the whole image into 
		# memory...
		logger.debug('Extracting info from JPEG file.')
		im = Image.open(fp)
		self.qualities = PIL_MODES_TO_QUALITIES[im.mode]
		self.width, self.height = im.size
		self.scale_factors = None
		self.tile_width = None
		self.tile_height = None

	def __from_tif(self, fp):
		logger.debug('Extracting info from TIFF file.')
		im = Image.open(fp)
		self.qualities = PIL_MODES_TO_QUALITIES[im.mode]
		self.width, self.height = im.size
		self.scale_factors = None
		self.tile_width = None
		self.tile_height = None

	def __from_jp2(self, fp):
		'''Get info about a JP2. 
		'''
		logger.debug('Extracting info from JP2 file.')
		self.qualities = ['native', 'bitonal']
		self.__native_quality = 'color' # TODO: HACK, this is an assumption

		jp2 = open(fp, 'rb')
		b = jp2.read(1)

		# Figure out color or greyscale. 
		# Depending color profiles; there's probably a better way (or more than
		# one, anyway.)
		# see: JP2 I.5.3.3 Colour Specification box
		window =  deque([], 4)
		while ''.join(window) != 'colr':
			b = jp2.read(1)
			c = struct.unpack('c', b)[0]
			window.append(c)

		b = jp2.read(1)
		meth = struct.unpack('B', b)[0]
		jp2.read(2) # over PREC and APPROX, 1 byte each
		
		# TODO: this isn't quite complete.
		if meth == 1: # Enumerated Colourspace
			enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
			logger.debug('Image contains an enumerated colourspace: %d' % (enum_cs,))
			# if enum_cs == 16:
			# 	self.__native_quality = 'color'
			# 	self.qualities += ['grey', 'color']
			if enum_cs == 17:
				self.__native_quality = 'grey'
				self.qualities += ['grey']
			else:
			 	self.__native_quality = 'color'
			 	self.qualities += ['grey', 'color']
		elif meth == 2:
			# (Restricted ICC profile). See pg 139 of the spec. Need to examine
			# the embedded profile.
			pass

		logger.debug('qualities: ' + str(self.qualities))

		b = jp2.read(1)
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) #skip over the SOC, 0x4F 
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x51: The SIZ marker segment
		if (ord(b) == 0x51):
			jp2.read(4) # get through Lsiz, Rsiz (16 bits each)
			self.width = int(struct.unpack(">HH", jp2.read(4))[1]) # Xsiz (32)
			self.height = int(struct.unpack(">HH", jp2.read(4))[1]) # Ysiz (32)
			logger.debug("width: " + str(self.width))
			logger.debug("height: " + str(self.height))
			jp2.read(8) # get through XOsiz , YOsiz  (32 bits each)
			self.tile_width = int(struct.unpack(">HH", jp2.read(4))[1]) # XTsiz (32)
			self.tile_height = int(struct.unpack(">HH", jp2.read(4))[1]) # YTsiz (32)
			logger.debug("tile width: " + str(self.tile_width))
			logger.debug("tile height: " + str(self.tile_height))	

		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x52: The COD marker segment
		if (ord(b) == 0x52):
			jp2.read(7) # through Lcod, Scod, SGcod (16 + 8 + 32 = 56 bits)
			levels = int(struct.unpack(">B", jp2.read(1))[0])
			logger.debug("levels: " + str(levels))	
			# TODO: correct?
			self.scale_factors = [pow(2, l) for l in range(0,levels)]
		jp2.close()

	def to_json(self):
		'''Serialize as json.
		Returns:
			str (json)
		'''
		# could probably just make a copy of self.__dict__ and delete a few entries
		d = {}
		d['@context'] = 'http://library.stanford.edu/iiif/image-api/1.1/context.json'
		d['@id'] = self.ident
		d['width'] = self.width
		d['height'] = self.height
		if self.scale_factors:
			d['scale_factors'] = self.scale_factors
		if self.tile_width:
			d['tile_width'] = self.tile_width
		if self.tile_height:
			d['tile_height'] = self.tile_height
		d['formats'] = self.formats
		d['qualities'] = self.qualities
		d['profile'] = COMPLIANCE

		return json.dumps(d)

# TODO, provide an alternate cache implementation using Mongo inst. 
# We'd probably still want some in memory, but we could avoid the file system. 
# Which impl to be used could be configured by class name

class InfoCache(object):
	"""A dict-like cache for ImageInfo objects. The n most recently used are 
	also kept in memory; all entries are on the file system.

	One twist: you put in an ImageInfo object, but get back a two-tuple, the 
	first member is the ImageInfo, the second member is the UTC date and time 
	for when the info was last modified.

	Note that not all dictionary methods are implemented; just basic getters, 
	put (`instance[indent] = info`), membership, and length. There are no 
	iterators, views, default, update, comparators, etc.

	Slots:
		root (str): See below
		size (int): See below.
		_dict (OrderedDict): The map.
		_lock (Lock): The lock.
	"""
	__slots__ = ('root','size','_dict','_lock', )
	def __init__(self, root, size=500):
		"""
		Args:
			root (str): 
				Path directory on the file system to be used for the cache.
			size (int): 
				Max entries before the we start popping (LRU).
		"""
		self.root = root
		self.size = size
		self._dict = OrderedDict()
		self._lock = Lock()

	def _get_fp(self,ident):
		return os.path.join(self.root,ident,'info.json')

	def get(self, ident):
		'''
		Returns:
			ImageInfo if it is in the cache, else None
		'''
		info_lastmod = None
		with self._lock:
			info_lastmod = self._dict.get(ident)
			if info_lastmod is not None:
				logger.debug('Info for %s read from memory' % (ident,))
		if info_lastmod is None:
			fp = self._get_fp(ident)
			if os.path.exists(fp):
				# from fs
				info = ImageInfo.from_json(fp)

				lastmod = datetime.utcfromtimestamp(os.path.getmtime(fp))
				info_lastmod = (info, lastmod)
				logger.debug('Info for %s read from file system' % (ident,))
				# into mem:
				self._dict[ident] = info_lastmod

		return info_lastmod

	def has_key(self, ident):
		return os.path.exists(self._get_fp(ident))

	def __len__(self):
		# c = 0
		# for root, dirnames, filenames in os.walk(self.root):
		# 	for filename in fnmatch.filter(filenames, STAR_DOT_JSON):
		# 		c+=1
		# return c
		w = os.walk
		ff = fnmatch.filter
		pat = STAR_DOT_JSON
		return len([_ for fp in ff(fps, pat) for r,dps,fps in w(self.root)])

	def __contains__(self, ident):
		return self.has_key(ident)

	def __getitem__(self, ident):
		info_lastmod = self.get(ident)
		if info_lastmod is None:
			raise KeyError
		else:
			return info_lastmod

	def __setitem__(self, ident, info):
		# to fs
		fp = self._get_fp(ident)
		dp = os.path.dirname(fp)
		if not os.path.exists(dp): 
			os.makedirs(dp, 0755)
			logger.debug('Created %s' % (dp,))


		f = open(fp, 'w')
		f.write(info.to_json())
		f.close()
		logger.debug('Created %s' % (fp,))

		# into mem
		lastmod = datetime.utcfromtimestamp(os.path.getmtime(fp))
		with self._lock:
			while len(self._dict) >= self.size:
				self._dict.popitem(last=False)
			self._dict[ident] = (info,lastmod)

	def __delitem__(self, ident):
		with self._lock:
			del self._dict[ident]
		fp = self._get_fp(ident)
		os.unlink(fp)
		os.removedirs(os.path.dirname(fp))




class ImageInfoException(loris_exception.LorisException): pass