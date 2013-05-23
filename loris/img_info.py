# img_info.py

from PIL import Image
from collections import OrderedDict
from collections import deque
from constants import IMG_API_NS, COMPLIANCE
from json import load
from log_config import get_logger
from threading import Lock
import loris_exception
import struct

logger = get_logger(__name__)

# TODO: we may want a little more exception handling in here.

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
		native_quality: 'color' or 'grey'
		src_format (str): as a three char file extension 
		src_img_fp (str): the absolute path on the file system
	'''
	__slots__ = ('scale_factors', 'width', 'tile_height', 'height', 
		'native_quality', 'tile_width', 'qualities', 'formats', 'ident', 
		'src_format', 'src_img_fp')

	@staticmethod
	def from_image_file(ident, src_img_fp, src_format):
		'''
		Args:
			src_img_fp (str): The absolute path to the image.
			src_format (str): The format of the image as a three-char str.
		'''
		# We're going to assume the image exists and the format is supported.
		# Exceptions should be raised by the resolver if that's not the case.
		new_inst = ImageInfo()
		new_inst.ident = ident
		new_inst.src_img_fp = src_img_fp
		new_inst.src_format = src_format

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
		try:
			f = open(path, 'r')
			j = load(f)
			logger.debug("HERE")
			new_inst.ident = j.get(u'identifier')
			new_inst.width = j.get(u'width')
			new_inst.height = j.get(u'height')
			new_inst.scale_factors = j.get(u'scale_factors')
			new_inst.tile_width = j.get(u'tile_width')
			new_inst.tile_height = j.get(u'tile_height')
			new_inst.formats = j.get(u'formats')
			new_inst.qualities = j.get(u'qualities')
		except Exception as e: # TODO: be more specific...
			iie = ImageInfoException(500, str(e))
		finally:
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
		self.native_quality = 'color' # TODO: HACK, this is an assumption
		self.qualities = ['native', 'bitonal']

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
		
		# TODO: this isn't quite complete. Need to account for 
		# meth == 2 (Restricted ICC profile). See pg 139 of the spec.
		if meth == 1: # Enumerated Colourspace
			enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
			logger.debug('Image contains an enumerated colourspace: %d' % (enum_cs,))
			# if enum_cs == 16:
			# 	self.native_quality = 'color'
			# 	self.qualities += ['grey', 'color']
			if enum_cs == 17:
				self.native_quality = 'grey'
				self.qualities += ['grey']
			else:
			 	self.native_quality = 'color'
			 	self.qualities += ['grey', 'color']
		else:
			# Restricted ICC profile.This Colour Specification box contains an 
			# ICC profile in the PROFILE field. This profile shall specify the 
			# transformation needed to convert the decompressed image data into 
			# the PCSXYZ, and shall conform to either the Monochrome Input or 
			# Three-Component Matrix-Based Input profile class, and contain all
			# the required tags specified therein, as defined in ICC.1:1998-09. 
			# As such, the value of the Profile Connection Space field in the 
			# profile header in the embedded profile shall be ‘XYZ\040’ 
			# (0x5859 5A20) indicating that the output colourspace of the 
			# profile is in the XYZ colourspace.

   			# http://www.color.org/icc-1_1998-09.pdf
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
			self.scale_factors = [str(pow(2, l)) for l in range(0,levels)]
		jp2.close()

	def to_json(self):
		'''Serialize as json.
		Returns:
			str
		'''
		# cheaper or not?
		j = '{'
		j += ' "identifier" : "' + self.ident + '",'
		j += ' "width" : ' + str(self.width) + ','
		j += ' "height" : ' + str(self.height) + ','
		if self.scale_factors:
			j += ' "scale_factors" : [' + ", ".join(map(str, self.scale_factors)) + '],'
		if self.tile_width:
			j += ' "tile_width" : ' + str(self.tile_width) + ','
		if self.tile_height:
			j += ' "tile_height" : ' + str(self.tile_height) + ','
		j += ' "formats" : [ "jpg", "png" ],'
		j += ' "qualities" : [' + ", ".join('"'+q+'"' for q in self.qualities) + '], '
		j += ' "profile" : "'+COMPLIANCE+'" '
		j += '}'
		return j

# TODO, provide an alternate implementation of the below using Mongo. Allow 
# which impl to be used to be configured by class name

class InfoCache(object):
	"""A thread-safe dict-like cache we can use to keep ImageInfo objects in
	memory and use as an LRU cache.

	Slots:
		size (int): See below.
		__dict (OrderedDict): The map.
		__lock (Lock): The lock.
	"""
	__slots__ = ('size', '__dict', '__lock')
	def __init__(self, size=500):
		"""
		Args:
			size (int): Max entries before the we start popping (LRU).
		"""
		self.size = size
		self.__dict = OrderedDict()
		self.__lock = Lock()

	def get(self, key):
		with self.__lock:
			return self.__dict.get(key)

	def __contains__(self, key):
		with self.__lock:
			return key in self.__dict

	def __getitem__(self, key):
		# It's not safe to get while the set of keys might be changing.
		with self.__lock:
			return self.__dict[key]

	def __setitem__(self, key, value):
		with self.__lock:
			while len(self.__dict) >= self.size:
				self.__dict.popitem(last=False)
			self.__dict[key] = value

	def __delitem__(self, key):
		with self.__lock:
			del self.__dict[key]

class ImageInfoException(loris_exception.LorisException): pass