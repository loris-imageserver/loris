# constants.py
# -*- coding: utf-8 -*-

IMG_API_NS='http://library.stanford.edu/iiif/image-api/ns/'

COMPLIANCE='http://library.stanford.edu/iiif/image-api/1.1/compliance.html#level2'

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