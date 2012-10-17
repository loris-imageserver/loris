# converters.py
from werkzeug.routing import BaseConverter
from parameters import RotationParameter, RegionParameter, SizeParameter

class RegionConverter(BaseConverter):
	"""Converter for IIIF region paramaters as specified.
	
	See <http://library.stanford.edu/iiif/image-api/#region>
	
	Returns: 
		RegionParameter
	"""
	def __init__(self, url_map):
		super(RegionConverter, self).__init__(url_map)
		self.regex = '[^/]+'

	def to_python(self, value):
		return RegionParameter(value)

	def to_url(self, value):
		return str(value)

class SizeConverter(BaseConverter):
	"""Converter for IIIF size paramaters.
	
	See <http://library.stanford.edu/iiif/image-api/#size>
	
	Returns: 
		SizeParameter
	"""
	def __init__(self, url_map):
		super(SizeConverter, self).__init__(url_map)
		self.regex = '[^/]+'
	
	def to_python(self, value):
		return SizeParameter(value)

	def to_url(self, value):
		return str(value)

class RotationConverter(BaseConverter):
	"""Converter for IIIF rotation paramaters.
	
	See <http://library.stanford.edu/iiif/image-api/#rotation>
	
	Returns: 
		RotationParameter
	"""
	def __init__(self, url_map):
		super(RotationConverter, self).__init__(url_map)
		self.regex = '\-?\d+'

	def to_python(self, value):
		return RotationParameter(value)

	def to_url(self, value):
		return str(value)