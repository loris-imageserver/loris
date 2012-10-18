# img_info.py
from collections import deque
from constants import IMG_API_NS, COMPLIANCE, FORMATS_SUPPORTED
from json import load
import struct
import xml.dom.minidom

class ImgInfo(object):
	"""Info about the image.

	See: <http://www-sul.stanford.edu/iiif/image-api/#info>

	Attributes:
		ident (str): The image identifier.
		width (int)
		height (int)
		tile_width (int)
		tile_height (int)
		levels [(int)]
		qualities [(str)]: 'native', 'bitonal', 'color', or 'grey'
		native_quality: 'color' or 'grey'
	"""
	# TODO: these should be slots and __init__ should just take a file name
	# from which we decide what to do based on the extension (maybe)
	def __init__(self):
		self.scale_factors = None
		self.width = None
		self.tile_height = None
		self.levels = None
		self.height = None
		self.native_quality = None
		self.tile_width = None
		self.qualities = None
		self.formats = None
		self.ident = None

	# Other fromXXX methods could be defined, hence the static constructors
	@staticmethod
	def fromJP2(path, img_id):
		"""Get info about a JP2. 

		There's enough going on here; make sure the file is available 
		(exists and readable) before passing it.
		
		See <http://library.stanford.edu/iiif/image-api/#info>

		Args:
			path (str): The absolute path to the image.
			img_id: The identifer for the image.

		Returns:
			ImgInfo
		"""
		info = ImgInfo()
		info.ident = img_id
		info.qualities = ['native', 'bitonal']

		jp2 = open(path, 'rb')
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
		if meth == 1: # Enumerated Colourspace
			enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
			if enum_cs == 16:
				info.native_quality = 'color'
				info.qualities += ['grey', 'color']
			elif enum_cs == 17:
				info.native_quality = 'grey'
				info.qualities += ['grey']
		#logr.debug('qualities: ' + str(info.qualities))

		b = jp2.read(1)
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) #skip over the SOC, 0x4F 
		
		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x51: The SIZ marker segment
		if (ord(b) == 0x51):
			jp2.read(4) # get through Lsiz, Rsiz (16 bits each)
			info.width = int(struct.unpack(">HH", jp2.read(4))[1]) # Xsiz (32)
			info.height = int(struct.unpack(">HH", jp2.read(4))[1]) # Ysiz (32)
			#logr.debug("width: " + str(info.width))
			#logr.debug("height: " + str(info.height))
			jp2.read(8) # get through XOsiz , YOsiz  (32 bits each)
			info.tile_width = int(struct.unpack(">HH", jp2.read(4))[1]) # XTsiz (32)
			info.tile_height = int(struct.unpack(">HH", jp2.read(4))[1]) # YTsiz (32)
			#logr.debug("tile width: " + str(info.tile_width))
			#logr.debug("tile height: " + str(info.tile_height))	

		while (ord(b) != 0xFF):	b = jp2.read(1)
		b = jp2.read(1) # 0x52: The COD marker segment
		if (ord(b) == 0x52):
			jp2.read(7) # through Lcod, Scod, SGcod (16 + 8 + 32 = 56 bits)
			info.levels = int(struct.unpack(">B", jp2.read(1))[0])
			#logr.debug("levels: " + str(info.levels)) 
		jp2.close()
			
		return info

	@staticmethod
	def unmarshal(path):
		"""Contruct an instance from an existing file.

		Args:
			path (str): the path to a JSON or XML file.

		Returns:
			ImgInfo

		Raises:
			Exception
		"""
		info = ImgInfo()
		if path.endswith('.json'):
			try:
				f = open(path, 'r')
				j = load(f)
				#logr.debug(j.get(u'identifier'))
				info.ident = j.get(u'identifier')
				info.width = j.get(u'width')
				info.height = j.get(u'height')
				info.scale_factors = j.get(u'scale_factors')
				info.tile_width = j.get(u'tile_width')
				info.tile_height = j.get(u'tile_height')
				info.formats = j.get(u'formats')
				info.qualities = j.get(u'qualities')
			finally:
				f.close()
		elif path.endswith('.xml'):
			# TODO!
			pass
		else:
			msg = 'Path passed to unmarshal does not contain XML or JSON' 
			raise Exception(msg)
		return info
	
	def marshal(self, to):
		"""Serialize the object as XML or json.

		Args:
			to (str): 'xml' or 'json'

		Returns:
			str.

		Raises:
			Exception
		"""
		if to == 'xml': return self._to_xml()
		elif to == 'json': return self._to_json()
		else:
			raise Exception('Argument to marshal must be \'xml\' or \'json\'')

	def _to_xml(self):
		"""Serialize as XML"""
		doc = xml.dom.minidom.Document()
		info = doc.createElementNS(IMG_API_NS, 'info')
		info.setAttribute('xmlns', IMG_API_NS)
		doc.appendChild(info)

		# identifier
		identifier = doc.createElementNS(IMG_API_NS, 'identifier')
		identifier.appendChild(doc.createTextNode(self.ident))
		info.appendChild(identifier)

		# width
		width = doc.createElementNS(IMG_API_NS, 'width')
		width.appendChild(doc.createTextNode(str(self.width)))
		info.appendChild(width)

		# height
		height = doc.createElementNS(IMG_API_NS, 'height')
		height.appendChild(doc.createTextNode(str(self.height)))
		info.appendChild(height)

		# scale_factors
		scale_factors = doc.createElementNS(IMG_API_NS, 'scale_factors')
		for s in range(1, self.levels+1):
			scale_factor = doc.createElementNS(IMG_API_NS, 'scale_factor')
			scale_factor.appendChild(doc.createTextNode(str(s)))
			scale_factors.appendChild(scale_factor)
		info.appendChild(scale_factors)

		# tile_width
		tile_width = doc.createElementNS(IMG_API_NS, 'tile_width')
		tile_width.appendChild(doc.createTextNode(str(self.tile_width)))
		info.appendChild(tile_width)

		# tile_height
		tile_height = doc.createElementNS(IMG_API_NS, 'tile_height')
		tile_height.appendChild(doc.createTextNode(str(self.tile_height)))
		info.appendChild(tile_height)

		# formats
		formats = doc.createElementNS(IMG_API_NS, 'formats')
		for f in FORMATS_SUPPORTED:
			fmt = doc.createElementNS(IMG_API_NS, 'format')
			fmt.appendChild(doc.createTextNode(f))
			formats.appendChild(fmt)
		info.appendChild(formats)

		# qualities
		qualities = doc.createElementNS(IMG_API_NS, 'qualities')
		for q in self.qualities:
			quality = doc.createElementNS(IMG_API_NS, 'quality')
			quality.appendChild(doc.createTextNode(q))
			qualities.appendChild(quality)
		info.appendChild(qualities)

		# profile
		profile = doc.createElementNS(IMG_API_NS, 'profile')
		profile.appendChild(doc.createTextNode(COMPLIANCE))
		info.appendChild(profile)
		return doc.toxml(encoding='UTF-8')
	
	def _to_json(self):
		"""Serialize as json"""
		# cheaper!
		j = '{'
		j += '  "identifier" : "' + self.ident + '", '
		j += '  "width" : ' + str(self.width) + ', '
		j += '  "height" : ' + str(self.height) + ', '
		j += '  "scale_factors" : [' + ", ".join(str(l) for l in range(1, self.levels+1)) + '], '
		j += '  "tile_width" : ' + str(self.tile_width) + ', '
		j += '  "tile_height" : ' + str(self.tile_height) + ', '
		j += '  "formats" : [ "jpg", "png" ], '
		j += '  "qualities" : [' + ", ".join('"'+q+'"' for q in self.qualities) + '], '
		j += '  "profile" : "'+COMPLIANCE+'"'
		j += '}'
		return j