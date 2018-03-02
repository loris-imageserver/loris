# img.py
#-*-coding:utf-8-*-

from __future__ import absolute_import

from datetime import datetime
import errno
from logging import getLogger
from os import path

try:
    from urllib.parse import unquote
except ImportError:  # Python 2
    from urllib import unquote

from loris.utils import mkdir_p, safe_rename, symlink

logger = getLogger(__name__)


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
