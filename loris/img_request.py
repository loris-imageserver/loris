# -*- encoding: utf-8

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
