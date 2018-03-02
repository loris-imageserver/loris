# img.py
#-*-coding:utf-8-*-

from __future__ import absolute_import

from datetime import datetime
import errno
from logging import getLogger
from os import path
import os

try:
    from urllib.parse import quote_plus, unquote
except ImportError:  # Python 2
    from urllib import quote_plus, unquote

import attr

from loris.parameters import RegionParameter, RotationParameter, SizeParameter
from loris.utils import mkdir_p, safe_rename, symlink

logger = getLogger(__name__)


@attr.s(slots=True, frozen=True)
class ImageRequest(object):
    """Stores information about a user's request for an image.

    Specifically, it holds a slightly more convenient representation of the
    request encoded in a IIIF URL:

        /{identifier}/{region}/{size}/{rotation}/{quality}.{format}

    """
    ident = attr.ib(converter=unquote)
    region_value = attr.ib(converter=unquote)
    size_value = attr.ib(converter=unquote)
    rotation_value = attr.ib()
    quality = attr.ib()
    format = attr.ib()

    @property
    def cache_path(self):
        path = os.path.join(
            self.ident,
            self.region_value,
            self.size_value,
            self.rotation_value,
            self.quality
        )
        return '%s.%s' % (path, self.format)

    def canonical_cache_path(self, img_info):
        path = os.path.join(
            self.ident,
            self.region_param(img_info).canonical_uri_value,
            self.size_param(img_info).canonical_uri_value,
            self.rotation_param().canonical_uri_value,
            self.quality
        )
        return '%s.%s' % (path, self.format)

    def is_canonical(self, img_info):
        return self.cache_path == self.canonical_cache_path(img_info)

    @property
    def request_path(self):
        path = os.path.join(
            quote_plus(self.ident),
            self.region_value,
            self.size_value,
            self.rotation_value,
            self.quality
        )
        return '%s.%s' % (path, self.format)

    def canonical_request_path(self, img_info):
        path = os.path.join(
            quote_plus(self.ident),
            self.region_param(img_info).canonical_uri_value,
            self.size_param(img_info).canonical_uri_value,
            self.rotation_param().canonical_uri_value,
            self.quality
        )
        return '%s.%s' % (path, self.format)

    def region_param(self, img_info):
        return RegionParameter(
            uri_value=self.region_value,
            img_info=img_info
        )

    def size_param(self, img_info):
        return SizeParameter(
            uri_value=self.size_value,
            region_parameter=self.region_param(img_info)
        )

    def rotation_param(self):
        return RotationParameter(uri_value=self.rotation_value)

    def request_resolution_too_large(self, max_size_above_full, img_info):
        if max_size_above_full == 0:
            return False

        region_param = self.region_param(img_info=img_info)
        size_param = self.size_param(img_info=img_info)

        max_width = region_param.pixel_w * max_size_above_full / 100
        max_height = region_param.pixel_h * max_size_above_full / 100

        return (size_param.w > max_width) or (size_param.h > max_height)


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

    def store(self, image_request, img_info, canonical_fp):
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
        if not image_request.is_canonical(img_info):
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
        request_fp = image_request.cache_path
        return path.realpath(path.join(self.cache_root, unquote(request_fp)))

    def get_canonical_cache_path(self, image_request, img_info):
        canonical_fp = image_request.canonical_cache_path(img_info=img_info)
        return path.realpath(path.join(self.cache_root, unquote(canonical_fp)))

    def create_dir_and_return_file_path(self, image_request, img_info):
        target_fp = self.get_canonical_cache_path(image_request, img_info)
        target_dp = path.dirname(target_fp)
        mkdir_p(target_dp)
        return target_fp

    def upsert(self, image_request, temp_fp, img_info):
        target_fp = self.create_dir_and_return_file_path(image_request, img_info)
        safe_rename(temp_fp, target_fp)
        return target_fp
