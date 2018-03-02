# -*- encoding: utf-8

import os

try:
    from urllib.parse import quote_plus, unquote
except ImportError:  # Python 2
    from urllib import quote_plus, unquote

import attr

from loris.parameters import RegionParameter, RotationParameter, SizeParameter


@attr.s(slots=True)
class ImageRequest(object):
    """Stores information about a request for an image."""
    ident = attr.ib(converter=unquote)
    region_value = attr.ib(converter=unquote)
    size_value = attr.ib(converter=unquote)
    rotation_value = attr.ib()
    quality = attr.ib()
    fmt = attr.ib()

    @property
    def cache_path(self):
        path = os.path.join(
            self.ident,
            self.region_value,
            self.size_value,
            self.rotation_value,
            self.quality
        )
        return '%s.%s' % (path, self.fmt)

    @property
    def request_path(self):
        path = os.path.join(
            quote_plus(self.ident),
            self.region_value,
            self.size_value,
            self.rotation_value,
            self.quality
        )
        return '%s.%s' % (path, self.fmt)

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
