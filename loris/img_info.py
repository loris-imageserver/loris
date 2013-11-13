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
		src_format (str): as a three char file extension 
		src_img_fp (str): the absolute path on the file system
		color_profile_bytes []: the emebedded color profile, if any
		self.color_profile_fp (str): path to the color profile on the file system
	'''
	__slots__ = ('scale_factors', 'width', 'tile_height', 'height', 
		'tile_width', 'qualities', 'formats', 'ident', 'src_format', 
		'src_img_fp', 'color_profile_bytes')

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
		elif new_inst.src_format == 'png':
			new_inst.__from_png(src_img_fp)
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
		self.color_profile_bytes = None

	def __from_png(self, fp):
		logger.debug('Extracting info from PNG file.')
		im = Image.open(fp)
		self.qualities = PIL_MODES_TO_QUALITIES[im.mode]
		self.width, self.height = im.size
		self.scale_factors = None
		self.tile_width = None
		self.tile_height = None
		self.color_profile_bytes = None

	def __from_tif(self, fp):
		logger.debug('Extracting info from TIFF file.')
		im = Image.open(fp)
		self.qualities = PIL_MODES_TO_QUALITIES[im.mode]
		self.width, self.height = im.size
		self.scale_factors = None
		self.tile_width = None
		self.tile_height = None
		self.color_profile_bytes = None

	def __from_jp2(self, fp):
		'''Get info about a JP2. 
		'''
		logger.debug('Extracting info from JP2 file.')
		self.qualities = ['native', 'bitonal']

		jp2 = open(fp, 'rb')
		b = jp2.read(1)

		window =  deque([], 4)

		while ''.join(window) != 'ihdr':
			b = jp2.read(1)
			c = struct.unpack('c', b)[0]
			window.append(c)
		self.height = int(struct.unpack(">I", jp2.read(4))[0]) # Height ("4-byte big endian unsigned integer"--pg. 136)
		self.width = int(struct.unpack(">I", jp2.read(4))[0]) # Width (ditto)
		logger.debug("width: " + str(self.width))
		logger.debug("height: " + str(self.height))

		# Figure out color or greyscale. 
		# Depending color profiles; there's probably a better way (or more than
		# one, anyway.)
		# see: JP2 I.5.3.3 Colour Specification box
		while ''.join(window) != 'colr':
			b = jp2.read(1)
			c = struct.unpack('c', b)[0]
			window.append(c)

		colr_meth = struct.unpack('B', jp2.read(1))[0]
		logger.debug('colr METH: %d' % (colr_meth,))
		jp2.read(2) # over PREC and APPROX, 1 byte each
		
		if colr_meth == 1: # Enumerated Colourspace
			self.color_profile_bytes = None
			enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
			logger.debug('Image contains an enumerated colourspace: %d' % (enum_cs,))
			logger.debug('Enumerated colourspace: %d' % (enum_cs))
			if enum_cs == 16: # sRGB
				self.qualities += ['grey', 'color']
			elif enum_cs == 17: # greyscale
				self.qualities += ['grey']
			elif enum_cs == 18: # sYCC
				pass
			else:
				msg = 'Enumerated colourspace is neither "16", "17", or "18". See jp2 spec pg. 139.'
				logger.warn(msg)
		elif colr_meth == 2:
			# (Restricted ICC profile).
			logger.debug('Image contains a restricted, embedded colour profile')
			# see http://www.color.org/icc-1_1998-09.pdf, page 18.
			profile_size_bytes = jp2.read(4)
			profile_size = int(struct.unpack(">I", profile_size_bytes)[0])
			logger.debug('profile size: %d' % (profile_size))
			self.color_profile_bytes = profile_size_bytes + jp2.read(profile_size-4)
		else:
			logger.warn('colr METH is neither "1" or "2". See jp2 spec pg. 139.')

		logger.debug('qualities: ' + str(self.qualities))

		b = jp2.read(1)
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) #skip over the SOC, 0x4F 
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x51: The SIZ marker segment
		if (ord(b) == 0x51):
			jp2.read(4) # through Lsiz, Rsiz (16 bits each)
			jp2.read(8) # through Xsiz, Ysiz (32 bits each)
			jp2.read(8) # through XOsiz, YOsiz  (32 bits each)
			self.tile_width = int(struct.unpack(">I", jp2.read(4))[0]) # XTsiz (32)
			self.tile_height = int(struct.unpack(">I", jp2.read(4))[0]) # YTsiz (32)
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

	def _get_info_fp(self,ident):
		return os.path.join(self.root,ident,'info.json')

	def _get_color_profile_fp(self,ident):
		return os.path.join(self.root,ident,'profile.icc')

	def get(self, ident):
		'''
		Returns:
			ImageInfo if it is in the cache, else None
		'''
		info_and_lastmod = None
		with self._lock:
			info_and_lastmod = self._dict.get(ident)
			if info_and_lastmod is not None:
				logger.debug('Info for %s read from memory' % (ident,))
		if info_and_lastmod is None:
			info_fp = self._get_info_fp(ident)
			if os.path.exists(info_fp):
				# from fs
				info = ImageInfo.from_json(info_fp)

				# color profile fp and bytes
				icc_fp = self._get_color_profile_fp(ident)
				if os.path.exists(icc_fp):
					with open(icc_fp, "rb") as f:
						info.color_profile_bytes = f.read()
				else: 
					info.color_profile_bytes = None

				lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
				info_and_lastmod = (info, lastmod)
				logger.debug('Info for %s read from file system' % (ident,))
				# into mem:
				self._dict[ident] = info_and_lastmod

		return info_and_lastmod

	def has_key(self, ident):
		return os.path.exists(self._get_info_fp(ident))

	def __len__(self):
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
		info_fp = self._get_info_fp(ident)
		dp = os.path.dirname(info_fp)
		if not os.path.exists(dp): 
			os.makedirs(dp, 0755)
			logger.debug('Created %s' % (dp,))

		with open(info_fp, 'w') as f:
			f.write(info.to_json())
			f.close()
			logger.debug('Created %s' % (info_fp,))

		if info.color_profile_bytes:
			icc_fp = self._get_color_profile_fp(ident)
			with open(icc_fp, 'wb') as f:
				f.write(info.color_profile_bytes)
				f.close()
				logger.debug('Created %s' % (icc_fp,))

		# into mem
		lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
		with self._lock:
			while len(self._dict) >= self.size:
				self._dict.popitem(last=False)
			self._dict[ident] = (info,lastmod)

	def __delitem__(self, ident):
		with self._lock:
			del self._dict[ident]

		info_fp = self._get_info_fp(ident)
		os.unlink(info_fp)

		icc_fp = self._getcolor_profile_bytes(ident)
		if os.path.exists(icc_fp):
			os.unlink(icc_fp)

		os.removedirs(os.path.dirname(info_fp))

class ImageInfoException(loris_exception.LorisException): pass


if __name__ == '__main__':
	from ImageCms import profileToProfile
	import cStringIO
	SRGB = "/home/jstroop/workspace/colorprofile/sRGB_v4_ICC_preference.icc"

	fp = '/home/jstroop/workspace/colorprofile/47102787.jp2'
	info = ImageInfo.from_image_file('id', 'http://id', fp, 'jp2', [])

	# cache = InfoCache('/tmp')
	# cache['id'] = info

	# info = cache['id']

	profile_from_jp2 = info[0].color_profile_bytes

	# get a bitmap from kdu_expand like normal
	original_bmp = Image.open('/home/jstroop/workspace/colorprofile/47102787.bmp')
	# map the profile to srgb
	profile_io = cStringIO.StringIO(profile_from_jp2)
	original_bmp = profileToProfile(original_bmp, profile_io, SRGB)
	# save!
	original_bmp.save('/home/jstroop/workspace/colorprofile/profile_to_bmp.jpg')
