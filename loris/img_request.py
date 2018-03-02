# -*- encoding: utf-8

try:
    from urllib.parse import quote_plus, unquote
except ImportError:  # Python 2
    from urllib import quote_plus, unquote

import attr


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
