# constants.py
# -*- coding: utf-8 -*-

COMPLIANCE = 'http://iiif.io/api/image/2/level2.json'
PROTOCOL = 'http://iiif.io/api/image'
CONTEXT = 'http://iiif.io/api/image/2/context.json'

OPTIONAL_FEATURES = [
  'canonical_link_header',
  'rotation_arbitrary',
  'size_above_full'
]

__formats = (
	('gif','image/gif'),
	('jp2','image/jp2'),
	('jpg','image/jpeg'),
	('pdf','application/pdf'),
	('png','image/png'),
	('tif','image/tiff'),
)

FORMATS_BY_EXTENSION = dict(__formats)

FORMATS_BY_MEDIA_TYPE = dict([(f[1],f[0]) for f in __formats])

SRC_FORMATS_SUPPORTED = (
	FORMATS_BY_MEDIA_TYPE['image/jpeg'],
	FORMATS_BY_MEDIA_TYPE['image/jp2'],
	FORMATS_BY_MEDIA_TYPE['image/tiff']
)

BITONAL = 'bitonal'
COLOR = 'color'
GREY = 'grey'
NATIVE = 'native'
QUALITIES = (BITONAL, COLOR, GREY, NATIVE)
