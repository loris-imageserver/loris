# constants.py
# -*- coding: utf-8 -*-

COMPLIANCE = 'http://iiif.io/api/image/2/level2.json'
PROTOCOL = 'http://iiif.io/api/image'
CONTEXT = 'http://iiif.io/api/image/2/context.json'

OPTIONAL_FEATURES = [
  'canonicalLinkHeader',
  'profileLinkHeader',
  'mirroring',
  'rotationArbitrary',
  'sizeAboveFull'
]

__formats = (
	('gif','image/gif'),
	('jp2','image/jp2'),
	('jpg','image/jpeg'),
	('pdf','application/pdf'),
	('png','image/png'),
	('tif','image/tiff'),
	('webp','image/webp'),
)

FORMATS_BY_EXTENSION = dict(__formats)

FORMATS_BY_MEDIA_TYPE = dict([(f[1],f[0]) for f in __formats])

BITONAL = 'bitonal'
COLOR = 'color'
GREY = 'gray'
DEFAULT = 'default'
QUALITIES = (BITONAL, COLOR, GREY, DEFAULT)
