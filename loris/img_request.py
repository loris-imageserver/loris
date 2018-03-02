# -*- encoding: utf-8

import os

try:
    from urllib.parse import quote_plus, unquote
except ImportError:  # Python 2
    from urllib import quote_plus, unquote

import attr

from loris.parameters import RegionParameter, SizeParameter


@attr.s(slots=True)
class ImageRequest(object):
    """Stores information about a request for an image."""
    ident = attr.ib(converter=unquote)
    region_value = attr.ib(converter=unquote)
    size_value = attr.ib(converter=unquote)
    rotation_value = attr.ib()
    quality = attr.ib()
    fmt = attr.ib()

    # These are lazily computed, and only set upon first access.
    _canonical_cache_path = attr.ib(init=False, default=None)
    _canonical_request_path = attr.ib(init=False, default=None)
    _cache_path = attr.ib(init=False, default=None)
    _request_path = attr.ib(init=False, default=None)
    _is_canonical = attr.ib(init=False, default=None)
    _region_param = attr.ib(init=False, default=None)
    _rotation_param = attr.ib(init=False, default=None)
    _size_param = attr.ib(init=False, default=None)

    @property
    def cache_path(self):
        if self._cache_path is None:
            p = os.path.join(
                self.ident,
                self.region_value,
                self.size_value,
                self.rotation_value,
                self.quality
            )
            self._cache_path = '%s.%s' % (p, self.fmt)
        return self._cache_path

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
            self._request_path = '%s.%s' % (p, self.fmt)
        return self._request_path

    def request_resolution_too_large(self, max_size_above_full, img_info):
        if max_size_above_full == 0:
            return False

        region_param = RegionParameter(
            uri_value=self.region_value,
            img_info=img_info
        )
        size_param = SizeParameter(
            uri_value=self.size_value,
            region_parameter=region_param
        )

        max_width = region_param.pixel_w * max_size_above_full / 100
        max_height = region_param.pixel_h * max_size_above_full / 100

        return (size_param.w > max_width) or (size_param.h > max_height)
