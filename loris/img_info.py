from collections import OrderedDict
from datetime import datetime
from logging import getLogger
from math import ceil
from threading import Lock
import json
import os

import attr
from PIL import Image

from loris.constants import COMPLIANCE, CONTEXT, OPTIONAL_FEATURES, PROTOCOL
from loris.identifiers import CacheNamer
from loris.jp2_extractor import JP2Extractor, JP2ExtractionError
from loris.loris_exception import ImageInfoException
from loris.utils import mkdir_p

logger = getLogger(__name__)

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


@attr.s(slots=True)
class Profile(object):
    """
    Represents a profile, as descriped in § 5.3 of the IIIF Image API spec.
    """
    compliance_uri = attr.ib(default='')
    description = attr.ib(default=attr.Factory(dict))


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Profile):
            # We only include the description in the JSON output if it's
            # non-empty.
            if obj.description:
                return [obj.compliance_uri, obj.description]
            else:
                return [obj.compliance_uri]
        return obj


class ImageInfo(JP2Extractor):
    '''Info about the image.
    See: <http://iiif.io/api/image/>

    Slots:
        width (int)
        height (int)
        scaleFactors [(int)]
        sizes [(str)]: the optimal sizes of the image to request
        tiles: [{}]
        service (dict): services associated with the image
        profile (Profile): Features supported by the server/available for
            this image

        src_img_fp (str): the absolute path on the file system [non IIIF]
        src_format (str): the format of the source image file [non IIIF]
        color_profile_bytes []: the embedded color profile, if any [non IIIF]
        auth_rules (dict): extra information about authorization [non IIIF]

    '''
    __slots__ = ('scaleFactors', 'width', 'tiles', 'height',
        'profile', 'sizes', 'service',
        'attribution', 'logo', 'license', 'auth_rules',
        'src_format', 'src_img_fp', 'color_profile_bytes')

    def __init__(self, app=None, src_img_fp="", src_format="", extra={}):
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

    @classmethod
    def from_json_fp(cls, path):
        """Contruct an instance from an existing file.

        Args:
            path (str): the path to a JSON file.

        Raises:
            Exception
        """
        with open(path, 'r') as f:
            return cls.from_json(f.read())

    @staticmethod
    def from_json(json_string):
        """Construct an instance from a JSON string.

        Args:
            j (str): A valid JSON string.

        """
        new_inst = ImageInfo()
        j = json.loads(json_string)

        new_inst.width = j.get('width')
        new_inst.height = j.get('height')
        # TODO: make sure these are resulting in error or Nones when
        # we load from the filesystem
        new_inst.tiles = j.get('tiles')
        new_inst.sizes = j.get('sizes')

        profile_args = tuple(j.get(u'profile', []))
        new_inst.profile = Profile(*profile_args)

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

        profile_description = {
            'formats': formats,
            'supports': OPTIONAL_FEATURES[:],
        }
        if (max_size_above_full == 0) or (max_size_above_full > 100):
            profile_description['supports'].append('sizeAboveFull')

        self.profile = Profile(
            compliance_uri=COMPLIANCE,
            description=profile_description
        )

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
        self.profile.description['qualities'] = PIL_MODES_TO_QUALITIES[im.mode]
        self.sizes = []

    def _from_jp2(self, fp):
        '''Get info about a JP2.
        '''
        logger.debug('Extracting info from JP2 file: %s' % fp)
        self.profile.description['qualities'] = ['default', 'bitonal']

        with open(fp, 'rb') as jp2:
            try:
                self.extract_jp2(jp2)
            except JP2ExtractionError as err:
                logger.warning(
                    "Error extracting JP2 %s: %r", fp, str(err)
                )
                raise ImageInfoException("Invalid JP2 file")

    def sizes_for_scales(self, scales):
        fn = ImageInfo.scale_dim
        return [(fn(self.width, sf), fn(self.height, sf)) for sf in scales]

    @staticmethod
    def scale_dim(dim_len, scale):
        return int(ceil(dim_len * 1.0/scale))

    def _get_iiif_info(self):
        d = {}
        d['@context'] = CONTEXT
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

    def to_iiif_json(self, base_uri):
        """returns only IIIF info (not Loris-specific info like src_format)"""
        d = self._get_iiif_info()
        d['@id'] = base_uri
        d['protocol'] = PROTOCOL
        return json.dumps(d, cls=EnhancedJSONEncoder)

    def to_full_info_json(self):
        """creates the info JSON that gets cached in the InfoCache"""
        d = self._get_iiif_info()
        d['_src_img_fp'] = self.src_img_fp
        d['_src_format'] = self.src_format
        d['_auth_rules'] = self.auth_rules
        return json.dumps(d, cls=EnhancedJSONEncoder)


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
    __slots__ = ( 'root', 'size', '_dict', '_lock')

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
        self._dict = OrderedDict()  # keyed by URL, so we don't need
                                    # to separate HTTP and HTTPS
        self._lock = Lock()

    def _get_ident_dir_path(self, ident):
        return os.path.join(self.root, CacheNamer.cache_directory_name(ident=ident))

    def _get_info_fp(self, ident):
        return os.path.join(self._get_ident_dir_path(ident), 'info.json')

    def _get_color_profile_fp(self, ident):
        return os.path.join(self._get_ident_dir_path(ident), 'profile.icc')

    def get(self, ident):
        '''
        Returns:
            ImageInfo if it is in the cache, else None
        '''
        info_and_lastmod = None
        with self._lock:
            info_and_lastmod = self._dict.get(ident)
        if info_and_lastmod is None:
            info_fp = self._get_info_fp(ident)
            if os.path.exists(info_fp):
                # from fs
                info = ImageInfo.from_json_fp(info_fp)

                icc_fp = self._get_color_profile_fp(ident)
                if os.path.exists(icc_fp):
                    with open(icc_fp, "rb") as f:
                        info.color_profile_bytes = f.read()
                else:
                    info.color_profile_bytes = None

                lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
                info_and_lastmod = (info, lastmod)
                logger.debug('Info for %s read from file system', ident)
                # into mem:
                self.__setitem__(ident, info, _to_fs=False)
        return info_and_lastmod

    def has_key(self, ident):
        return os.path.exists(self._get_info_fp(ident))

    def __contains__(self, ident):
        return self.has_key(ident)

    def __getitem__(self, ident):
        info_lastmod = self.get(ident)
        if info_lastmod is None:
            raise KeyError
        else:
            return info_lastmod

    def __setitem__(self, ident, info, _to_fs=True):
        info_fp = self._get_info_fp(ident)
        if _to_fs:
            # to fs
            logger.debug('ident passed to __setitem__: %s', ident)
            dp = os.path.dirname(info_fp)
            mkdir_p(dp)
            logger.debug('Created %s', dp)

            with open(info_fp, 'w') as f:
                f.write(info.to_full_info_json())
            logger.debug('Created %s', info_fp)


            if info.color_profile_bytes:
                icc_fp = self._get_color_profile_fp(ident)
                with open(icc_fp, 'wb') as f:
                    f.write(info.color_profile_bytes)
                logger.debug('Created %s', icc_fp)

        # into mem
        # The info file cache on disk must already exist before
        # this is called - it's where the mtime gets drawn from.
        # aka, nothing outside of this class should be using
        # to_fs=False
        if self.size > 0:
            lastmod = datetime.utcfromtimestamp(os.path.getmtime(info_fp))
            with self._lock:
                self._dict[ident] = (info,lastmod)
                while len(self._dict) > self.size:
                    self._dict.popitem(last=False)

    def __delitem__(self, ident):
        with self._lock:
            del self._dict[ident]

        info_fp = self._get_info_fp(ident)
        os.unlink(info_fp)

        icc_fp = self._get_color_profile_fp(ident)
        if os.path.exists(icc_fp):
            os.unlink(icc_fp)

        os.removedirs(os.path.dirname(info_fp))

    def __len__(self):
        return len(self._dict)
