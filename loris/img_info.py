# img_info.py

from __future__ import absolute_import

from collections import deque, OrderedDict
from datetime import datetime
from logging import getLogger
from math import ceil
from threading import Lock
import json
import os
import struct

try:
    from urllib.parse import unquote
except ImportError:  # Python 2
    from urllib import unquote

from PIL import Image

from loris.constants import COMPLIANCE, CONTEXT, OPTIONAL_FEATURES, PROTOCOL
from loris.loris_exception import ImageInfoException
from loris.utils import mkdir_p

logger = getLogger(__name__)

STAR_DOT_JSON = '*.json'

PIL_MODES_TO_QUALITIES = {
    # Thanks to http://stackoverflow.com/a/1996609/714478
    '1' : ['default','bitonal'],
    'L' : ['default','gray','bitonal'],
    'LA' : ['default','gray','bitonal'],
    'P' : ['default','gray','bitonal'],
    'RGB': ['default','color','gray','bitonal'],
    'RGBA': ['default','color','gray','bitonal'],
    'RGBX': ['default','color','gray','bitonal'],
    'CMYK': ['default','color','gray','bitonal'],
    'YCbCr': ['default','color','gray','bitonal'],
    'I': ['default','color','gray','bitonal'],
    'F': ['default','color','gray','bitonal']
}

class ImageInfo(object):
    '''Info about the image.
    See: <http://iiif.io/api/image/>

    Slots:
        ident (str): The image identifier.
        width (int)
        height (int)
        scaleFactors [(int)]
        sizes [(str)]: the optimal sizes of the image to request
        tiles: [{}]
        protocol (str): the protocol URI (constant)
        service (dict): services associated with the image
        profile []: Features supported by the server/available for this image

        src_img_fp (str): the absolute path on the file system [non IIIF]
        src_format (str): the format of the source image file [non IIIF]
        color_profile_bytes []: the embedded color profile, if any [non IIIF]
        auth_rules (dict): extra information about authorization [non IIIF]

    '''
    __slots__ = ('scaleFactors', 'width', 'tiles', 'height',
        'ident', 'profile', 'protocol', 'sizes', 'service',
        'attribution', 'logo', 'license', 'auth_rules',
        'src_format', 'src_img_fp', 'color_profile_bytes')

    def __init__(self, app=None, ident="", src_img_fp="", src_format="", extra={}):

        self.protocol = PROTOCOL
        self.ident = ident
        self.src_img_fp = src_img_fp
        self.src_format = src_format
        self.attribution = None
        self.logo = None
        self.license = None
        self.service = {}
        self.auth_rules = extra

        # The extraInfo parameter can be used to override specific attributes.
        # If there are extra attributes, drop an error.
        bad_attrs = []
        for (k, v) in extra.get('extraInfo', {}).items():
            try:
                setattr(self, k, v)
            except AttributeError:
                bad_attrs.append(k)
        if bad_attrs:
            raise ImageInfoException(
                "Invalid parameters in extraInfo: %s." % ', '.join(bad_attrs)
            )

        # If constructed from JSON, the pixel info will already be processed
        if app:
            try:
                formats = app.transformers[src_format].target_formats
            except KeyError:
                raise ImageInfoException(
                    "Didn't get a source format, or at least one we recognize (%r)." %
                    src_format
                )
            # Finish setting up the info from the image file
            self.from_image_file(formats, app.max_size_above_full)

    @staticmethod
    def from_json(path):
        """Contruct an instance from an existing file.

        Args:
            path (str): the path to a JSON file.

        Raises:
            Exception
        """
        new_inst = ImageInfo()
        with open(path, 'r') as f:
            j = json.load(f)

        new_inst.ident = j.get(u'@id')
        new_inst.width = j.get(u'width')
        new_inst.height = j.get(u'height')
        # TODO: make sure these are resulting in error or Nones when
        # we load from the filesystem
        new_inst.tiles = j.get(u'tiles')
        new_inst.sizes = j.get(u'sizes')
        new_inst.profile = j.get(u'profile')
        new_inst.service = j.get('service', {})

        # Also add src_img_fp if available
        new_inst.src_img_fp = j.get('_src_img_fp', '')
        new_inst.src_format = j.get('_src_format', '')
        new_inst.auth_rules = j.get('_auth_rules', {})

        return new_inst

    def from_image_file(self, formats=[], max_size_above_full=200):
        '''
        Args:
            ident (str): The URI for the image.
            formats ([str]): The derivative formats the application can produce.
        '''
        # Assumes that the image exists and the format is supported. Exceptions
        # should be raised by the resolver if that's not the case.
        self.tiles = []
        self.sizes = None
        self.scaleFactors = None
        local_profile = {'formats' : formats, 'supports' : OPTIONAL_FEATURES[:]}
        if max_size_above_full == 0 or max_size_above_full > 100:
            local_profile['supports'].append('sizeAboveFull')
        self.profile = [ COMPLIANCE, local_profile ]

        if self.src_format == 'jp2':
            self._from_jp2(self.src_img_fp)
        elif self.src_format  in ('jpg','tif','png'):
            self._extract_with_pillow(self.src_img_fp)
        else:
            raise ImageInfoException(
                "Didn't get a source format, or at least one we recognize (%r)." %
                self.src_format
            )
        # in case of ii = ImageInfo().from_image_file()
        return self

    def _extract_with_pillow(self, fp):
        logger.debug('Extracting info from file with Pillow.')
        im = Image.open(fp)
        self.width, self.height = im.size
        self.tiles = []
        self.color_profile_bytes = None
        self.profile[1]['qualities'] = PIL_MODES_TO_QUALITIES[im.mode]
        self.sizes = []

    def _from_jp2(self, fp):
        '''Get info about a JP2.
        '''
        logger.debug('Extracting info from JP2 file: %s' % fp)
        self.profile[1]['qualities'] = ['default', 'bitonal']

        scaleFactors = []

        with open(fp, 'rb') as jp2:

            #check that this is a jp2 file
            initial_bytes = jp2.read(24)
            if (not initial_bytes[:12] == '\x00\x00\x00\x0cjP  \r\n\x87\n') or \
                (not initial_bytes[16:] == 'ftypjp2 '):
                logger.warning('Invalid JP2 file at %s', fp)
                raise ImageInfoException('Invalid JP2 file')

            #grab width and height
            window = deque([], 4)
            b = jp2.read(1)
            while ''.join(window) != 'ihdr':
                b = jp2.read(1)
                c = struct.unpack('c', b)[0]
                window.append(c)
            self.height = int(struct.unpack(">I", jp2.read(4))[0]) # height (pg. 136)
            self.width = int(struct.unpack(">I", jp2.read(4))[0]) # width
            logger.debug("width: %s", self.width)
            logger.debug("height: %s", self.height)

            # Figure out color or grayscale.
            # Depending color profiles; there's probably a better way (or more than
            # one, anyway.)
            # see: JP2 I.5.3.3 Colour Specification box
            while ''.join(window) != 'colr':
                b = jp2.read(1)
                c = struct.unpack('c', b)[0]
                window.append(c)

            colr_meth = struct.unpack('B', jp2.read(1))[0]
            logger.debug('colr METH: %d', colr_meth)

            # PREC and APPROX, 1 byte each
            colr_prec = struct.unpack('b', jp2.read(1))[0]
            colr_approx = struct.unpack('B', jp2.read(1))[0]
            logger.debug('colr PREC: %d', colr_prec)
            logger.debug('colr APPROX: %d', colr_approx)

            if colr_meth == 1: # Enumerated Colourspace
                self.color_profile_bytes = None
                enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
                logger.debug('Image contains an enumerated colourspace: %d', enum_cs)
                logger.debug('Enumerated colourspace: %d', enum_cs)
                if enum_cs == 16: # sRGB
                    self.profile[1]['qualities'] += ['gray', 'color']
                elif enum_cs == 17: # grayscale
                    self.profile[1]['qualities'] += ['gray']
                elif enum_cs == 18: # sYCC
                    pass
                else:
                    msg =  'Enumerated colourspace is neither "16", "17", or "18". '
                    msg += 'See jp2 spec pg. 139.'
                    logger.warn(msg)
            elif colr_meth == 2:
                # (Restricted ICC profile).
                logger.debug('Image contains a restricted, embedded colour profile')
                # see http://www.color.org/icc-1_1998-09.pdf, page 18.
                self.assign_color_profile(jp2)
            else:
                logger.warn('colr METH is neither "1" or "2". See jp2 spec pg. 139.')

                # colr METH 3 = Any ICC method, colr METH 4 = Vendor Colour method
                # See jp2 spec pg. 182 -  Table M.24 (Color spec box legal values)
                if colr_meth <= 4 and -128 <= colr_prec <= 127 and 1 <= colr_approx <= 4:
                    self.assign_color_profile(jp2)

            logger.debug('qualities: %s', self.profile[1]['qualities'])

            window =  deque(jp2.read(2), 2)
            while map(ord, window) != [0xFF, 0x4F]: # (SOC - required, see pg 14)
                window.append(jp2.read(1))
            while map(ord, window) != [0xFF, 0x51]:  # (SIZ  - required, see pg 14)
                window.append(jp2.read(1))
            jp2.read(20) # through Lsiz (16), Rsiz (16), Xsiz (32), Ysiz (32), XOsiz (32), YOsiz (32)
            tile_width = int(struct.unpack(">I", jp2.read(4))[0]) # XTsiz (32)
            tile_height = int(struct.unpack(">I", jp2.read(4))[0]) # YTsiz (32)
            logger.debug("tile width: %s", tile_width)
            logger.debug("tile height: %s", tile_height)
            self.tiles.append( { 'width' : tile_width } )
            if tile_width != tile_height:
                self.tiles[0]['height'] = tile_height
            jp2.read(10) # XTOsiz (32), YTOsiz (32), Csiz (16)

            window =  deque(jp2.read(2), 2)
            # while (ord(b) != 0xFF): b = jp2.read(1)
            # b = jp2.read(1) # 0x52: The COD marker segment
            while map(ord, window) != [0xFF, 0x52]:  # (COD - required, see pg 14)
                window.append(jp2.read(1))

            jp2.read(7) # through Lcod (16), Scod (8), SGcod (32)
            levels = int(struct.unpack(">B", jp2.read(1))[0])
            logger.debug("levels: %s", levels)
            scaleFactors = [pow(2, l) for l in range(0,levels+1)]
            self.tiles[0]['scaleFactors'] = scaleFactors
            jp2.read(4) # through code block stuff

            # We may have precincts if Scod or Scoc = xxxx xxx0
            # But we don't need to examine as this is the last variable in the
            # COD segment. Instead check if the next byte == 0xFF. If it is,
            # we don't have a Precint size parameter and we've moved on to either
            # the COC (optional, marker = 0xFF53) or the QCD (required,
            # marker = 0xFF5C)
            b = jp2.read(1)
            if ord(b) != 0xFF:
                if self.tiles[0]['width'] == self.width \
                    and self.tiles[0].get('height') in (self.height, None):
                    # Clear what we got above in SIZ and prefer this. This could
                    # technically break as it's possible to have precincts inside tiles.
                    # Let's wait for that to come up....
                    self.tiles = []

                    for level in range(levels+1):
                        i = int(bin(struct.unpack(">B", b)[0])[2:].zfill(8),2)
                        x = i&15
                        y = i >> 4
                        w = 2**x
                        h = 2**y
                        b = jp2.read(1)
                        try:
                            entry = next((i for i in self.tiles if i['width'] == w))
                            entry['scaleFactors'].append(pow(2, level))
                        except StopIteration:
                            self.tiles.append({'width':w, 'scaleFactors':[pow(2, level)]})

        self.sizes = [
            {'width': width, 'height': height}
            for width, height in self.sizes_for_scales(scaleFactors)
        ]
        self.sizes.sort(key=lambda size: max([size['width'], size['height']]))

    def assign_color_profile(self, jp2):
        profile_size_bytes = jp2.read(4)
        profile_size = int(struct.unpack(">I", profile_size_bytes)[0])

        logger.debug('profile size: %d', profile_size)
        self.color_profile_bytes = profile_size_bytes + jp2.read(profile_size-4)

        # This is an assumption for now (i.e. that if you have a colour profile
        # embedded, you're probably working with color images.
        self.profile[1]['qualities'] += ['gray', 'color']

    def sizes_for_scales(self, scales):
        fn = ImageInfo.scale_dim
        return [(fn(self.width, sf), fn(self.height, sf)) for sf in scales]

    @staticmethod
    def scale_dim(dim_len, scale):
        return int(ceil(dim_len * 1.0/scale))

    def _get_iiif_info(self):
        """returns only IIIF info (not Loris-specific info like src_format)"""
        d = {}
        d['@context'] = CONTEXT
        d['@id'] = self.ident
        d['protocol'] = self.protocol
        d['profile'] = self.profile
        d['width'] = self.width
        d['height'] = self.height
        if self.tiles:
            d['tiles'] = self.tiles
        d['sizes'] = self.sizes
        if self.service:
            d['service'] = self.service
        if self.attribution:
            d['attribution'] = self.attribution
        if self.logo:
            d['logo'] = self.logo
        if self.license:
            d['license'] = self.license

        return d

    def to_iiif_json(self):
        d = self._get_iiif_info()
        return json.dumps(d)

    def to_full_info_json(self):
        """creates the info JSON that gets cached in the InfoCache"""
        d = self._get_iiif_info()
        d['_src_img_fp'] = self.src_img_fp
        d['_src_format'] = self.src_format
        d['_auth_rules'] = self.auth_rules
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
        http_root (str): See below
        https_root (str): See below
        size (int): See below.
        _dict (OrderedDict): The map.
        _lock (Lock): The lock.
    """
    __slots__ = ( 'http_root', 'https_root', 'size', '_dict', '_lock')

    def __init__(self, root, size=500):
        """
        Args:
            root (str):
                Path directory on the file system to be used for the cache.
            size (int):
                Max entries before the we start popping (LRU).
        """
        self.http_root = os.path.join(root, 'http')
        self.https_root = os.path.join(root, 'https')
        self.size = size
        self._dict = OrderedDict()  # keyed by URL, so we don't need
                                    # to separate HTTP and HTTPS
        self._lock = Lock()

    def _which_root(self, request):
        if request.url.startswith('https'):
            return self.https_root
        else:
            return self.http_root

    @staticmethod
    def ident_from_request(request):
        return '/'.join(request.path[1:].split('/')[:-1])

    def _get_info_fp(self, request):
        ident = InfoCache.ident_from_request(request)
        cache_root = self._which_root(request)
        path = os.path.join(cache_root, unquote(ident), 'info.json')
        return path

    def _get_color_profile_fp(self, request):
        ident = InfoCache.ident_from_request(request)
        cache_root = self._which_root(request)
        path = os.path.join(cache_root, unquote(ident), 'profile.icc')
        return path

    def get(self, request):
        '''
        Returns:
            ImageInfo if it is in the cache, else None
        '''
        info_and_lastmod = None
        with self._lock:
            info_and_lastmod = self._dict.get(request.url)
        if info_and_lastmod is None:
            info_fp = self._get_info_fp(request)
            if os.path.exists(info_fp):
                # from fs
                info = ImageInfo.from_json(info_fp)

                icc_fp = self._get_color_profile_fp(request)
                if os.path.exists(icc_fp):
                    with open(icc_fp, "rb") as f:
                        info.color_profile_bytes = f.read()
                else:
                    info.color_profile_bytes = None

                lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
                info_and_lastmod = (info, lastmod)
                logger.debug('Info for %s read from file system', request)
                # into mem:
                self._dict[request.url] = info_and_lastmod

        return info_and_lastmod

    def has_key(self, request):
        return os.path.exists(self._get_info_fp(request))

    def __contains__(self, request):
        return self.has_key(request)

    def __getitem__(self, request):
        info_lastmod = self.get(request)
        if info_lastmod is None:
            raise KeyError
        else:
            return info_lastmod

    def __setitem__(self, request, info):
        # to fs
        logger.debug('request passed to __setitem__: %s', request)
        info_fp = self._get_info_fp(request)
        dp = os.path.dirname(info_fp)
        mkdir_p(dp)
        logger.debug('Created %s', dp)

        with open(info_fp, 'w') as f:
            f.write(info.to_full_info_json())
        logger.debug('Created %s', info_fp)


        if info.color_profile_bytes:
            icc_fp = self._get_color_profile_fp(request)
            with open(icc_fp, 'wb') as f:
                f.write(info.color_profile_bytes)
            logger.debug('Created %s', icc_fp)

        # into mem
        lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
        with self._lock:
            while len(self._dict) >= self.size:
                self._dict.popitem(last=False)
            self._dict[request.url] = (info,lastmod)

    def __delitem__(self, request):
        with self._lock:
            del self._dict[request.url]

        info_fp = self._get_info_fp(request)
        os.unlink(info_fp)

        icc_fp = self._get_color_profile_fp(request)
        if os.path.exists(icc_fp):
            os.unlink(icc_fp)

        os.removedirs(os.path.dirname(info_fp))

    def __len__(self):
        return len(self._dict)
