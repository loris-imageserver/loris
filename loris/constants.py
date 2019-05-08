# constants.py
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import re

COMPLIANCE = 'http://iiif.io/api/image/2/level2.json'
PROTOCOL = 'http://iiif.io/api/image'
CONTEXT = 'http://iiif.io/api/image/2/context.json'

OPTIONAL_FEATURES = [
  'canonicalLinkHeader',
  'profileLinkHeader',
  'mirroring',
  'rotationArbitrary',
  'regionSquare'
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

#map 4-letter extensions to the 3-letter image format
EXTENSION_MAP = {
        'jpeg': 'jpg',
        'tiff': 'tif',
    }

_IDENT = r'(?P<ident>.+)'
_REGION = r'(?P<region>[-? \w:\.\,]+)'
_SIZE = r'(?P<size>\!?[\w:\.\,]+)'
_ROTATION = r'(?P<rotation>\!?\d+\.?\d*)'
_QUALITY = r'(?P<quality>(color|gray|bitonal|default))'
_FORMAT = r'(?P<format>\w+)'

_IMAGE_REQUEST = r'/%s/%s/%s/%s/%s.%s' % (_IDENT, _REGION, _SIZE, _ROTATION, _QUALITY, _FORMAT)
IMAGE_RE = re.compile(_IMAGE_REQUEST)

_INFO_REQUEST = r'/%s/%s' % (_IDENT, 'info.json')
INFO_RE = re.compile(_INFO_REQUEST)

LOOSER_IMAGE_RE = re.compile(r'/%s/\w+/\w+/\w+/\w.\w' % _IDENT)
