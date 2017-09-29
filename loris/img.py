# img.py
#-*-coding:utf-8-*-

from __future__ import absolute_import

from datetime import datetime
import errno
from logging import getLogger
from os import path, rename

try:
    from urllib.parse import quote_plus, unquote
except ImportError:  # Python 2
    from urllib import quote_plus, unquote

from loris.loris_exception import ImageException
from loris.parameters import RegionParameter, RotationParameter, SizeParameter
from loris.utils import mkdir_p, symlink

logger = getLogger(__name__)

class ImageRequest(object):
    '''
    Slots:
        ident (str)
        region_value (str):
            copied exactly from the URI
        size_value (str)
            copied exactly from the URI
        rotation_value (str)
            copied exactly from the URI
        quality (str)
            copied exactly from the URI
        format (str)
            3 char string from the URI, (derived from) HTTP headers, or else the
            default.
        region_param (parameters.RegionParameter):
            See RegionParameter.__slots__. The region is represented there as
            both pixels and decmials.
        size_param (parameters.SizeParameter)
            See SizeParameter.__slots__.
        rotation_param (parameters.RotationParameter)
            See RotationParameter.__slots__.
        info (ImageInfo):
        is_canonical (bool):
            True if this is a canonical path.
        as_path (str):
            Useful as a relative path from a cache root. Based on the original
            request values.
        canonical_as_path (str):
            Useful as a relative path from a cache root. Based on values
            normalized to the canonical request syntax.
        request_path
            Path of the request for tacking on to the service host and creating
            a URI based on the original request.
        canonical_request_path
            Path of the request for tacking on to the service host and creating
            a URI based on the normalized ('canonical') values.
            ('canonical') values.
        Raises:


    '''
    __slots__ = (
        '_canonical_cache_path',
        '_canonical_request_path',
        '_cache_path',
        '_info',
        '_is_canonical',
        '_region_param',
        '_request_path',
        '_rotation_param',
        '_size_param',
        'format',
        'ident',
        'quality',
        'region_value',
        'rotation_value',
        'size_value'
    )

    def __init__(self, ident, region, size, rotation, quality, target_format):

        self.ident, self.region_value, self.size_value = map(unquote, (ident, region, size))
        self.rotation_value = rotation
        self.quality = quality
        self.format = target_format

        logger.debug('region slice: %s', region)
        logger.debug('size slice: %s', size)
        logger.debug('rotation slice: %s', rotation)
        logger.debug('quality slice: %s', self.quality)
        logger.debug('format extension: %s', self.format)

        # These aren't set until we first access them
        self._canonical_cache_path = None
        self._canonical_request_path = None
        self._cache_path = None
        self._request_path = None

        self._is_canonical = None

        self._region_param = None
        self._rotation_param = None
        self._size_param = None

        # This is a little awkward. We may need it, but not right away (only if we're
        # filling out the param slots), so the user (of the class) has to set
        # it before accessing most of the above.
        self._info = None

    @property
    def region_param(self):
        if self._region_param is None:
            self._region_param = RegionParameter(self.region_value, self.info)
        return self._region_param

    @property
    def size_param(self):
        if self._size_param is None:
            self._size_param = SizeParameter(self.size_value, self.region_param)
        return self._size_param

    @property
    def rotation_param(self):
        if self._rotation_param is None:
            self._rotation_param = RotationParameter(self.rotation_value)
        return self._rotation_param

    @property
    def request_path(self):
        if self._request_path is None:
            p = '/'.join((
                quote_plus(self.ident),
                self.region_value,
                self.size_value,
                self.rotation_value,
                self.quality
            ))
            self._request_path = '%s.%s' % (p,self.format)
        return self._request_path

    @property
    def canonical_request_path(self):
        if self._canonical_request_path is None:
            p = '/'.join((
                quote_plus(self.ident),
                self.region_param.canonical_uri_value,
                self.size_param.canonical_uri_value,
                self.rotation_param.canonical_uri_value,
                self.quality
            ))
            self._canonical_request_path = '%s.%s' % (p,self.format)
        return self._canonical_request_path

    @property
    def as_path(self):
        if self._cache_path is None:
            p = path.join(self.ident,
                self.region_value,
                self.size_value,
                self.rotation_value,
                self.quality
            )
            self._cache_path = '%s.%s' % (p, self.format)
        return self._cache_path

    @property
    def canonical_as_path(self):
        if self._canonical_cache_path is None:
            p = path.join(self.ident,
                self.region_param.canonical_uri_value,
                self.size_param.canonical_uri_value,
                self.rotation_param.canonical_uri_value,
                self.quality
            )
            self._canonical_cache_path = '%s.%s' % (p, self.format)
        return self._canonical_cache_path

    @property
    def is_canonical(self):
        if self._is_canonical is None:
            self._is_canonical = self.as_path == self.canonical_as_path
        return self._is_canonical

    @property
    def info(self):
        if self._info is None:
            # For dev purposes only. This should never happen.
            raise ImageException(http_status=500, message='Image.info not set!')
        else:
            return self._info

    @info.setter
    def info(self, i):
        self._info = i

    def request_resolution_too_large(self, max_size_above_full):
        if max_size_above_full == 0:
            return False
        max_width = self.region_param.pixel_w * max_size_above_full / 100
        max_height = self.region_param.pixel_h * max_size_above_full / 100
        if self.size_param.w > max_width or \
                self.size_param.h > max_height:
            return True
        return False


class ImageCache(dict):
    '''
    '''
    def __init__(self, cache_root):
        self.cache_root = cache_root

    def __contains__(self, image_request):
        return path.exists(self.get_request_cache_path(image_request))

    def __getitem__(self, image_request):
        try:
            cache_fp = self.get_request_cache_path(image_request)
            last_mod = datetime.utcfromtimestamp(path.getmtime(cache_fp))
            return (cache_fp, last_mod)
        except OSError as err:
            if err.errno == errno.ENOENT:
                raise KeyError(image_request)
            else:
                raise

    def __setitem__(self, image_request, canonical_fp):
        # Because we're working with files, it's more practical to put derived
        # images where the cache expects them when they are created (i.e. by
        # Loris#_make_image()), so __setitem__, as defined by the dict API
        # doesn't really work. Instead, the logic related to where an image
        # should be put is encapulated in the ImageCache#get_request_cache_path
        # and ImageCache#get_canonical_cache_path methods.
        #
        # Instead, __setitem__ simply makes a symlink in the cache from the
        # requested syntax to the canonical syntax to enable faster lookups of
        # the same non-canonical request the next time.
        #
        # So: when Loris#_make_image is called, it gets a path from
        # ImageCache#get_canonical_cache_path and passes that to the
        # transformer.
        if not image_request.is_canonical:
            requested_fp = self.get_request_cache_path(image_request)
            symlink(src=canonical_fp, dst=requested_fp)

    def __delitem__(self, image_request):
        # if we ever decide to start cleaning our own cache...
        pass

    def get(self, image_request):
        '''Returns (str, ):
            The path to the file or None if the file does not exist.
        '''
        try:
            return self[image_request]
        except KeyError:
            return None

    def get_request_cache_path(self, image_request):
        request_fp = image_request.as_path
        return path.realpath(path.join(self.cache_root, unquote(request_fp)))

    def get_canonical_cache_path(self, image_request):
        canonical_fp = image_request.canonical_as_path
        return path.realpath(path.join(self.cache_root, unquote(canonical_fp)))

    def create_dir_and_return_file_path(self, image_request):
        target_fp = self.get_canonical_cache_path(image_request)
        target_dp = path.dirname(target_fp)
        mkdir_p(target_dp)
        return target_fp

    def upsert(self, image_request, temp_fp):
        target_fp = self.create_dir_and_return_file_path(image_request)
        rename(temp_fp, target_fp)
        return target_fp
