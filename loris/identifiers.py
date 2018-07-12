# -*- encoding: utf-8
"""
Utilities for dealing with identifiers.
"""

import hashlib
import os
import re

try:
    from urllib.parse import quote_plus
except ImportError:  # Python 2
    from urllib import quote_plus


class IdentRegexChecker(object):
    """
    Allows a user to specify a regex that matches all identifiers.

    This can allow us to skip making a network/disk request if the identifier
    is invalid -- we can return a 404 faster.

    """
    def __init__(self, ident_regex):
        if ident_regex is not None:
            self.ident_regex = re.compile(ident_regex)
        else:
            self.ident_regex = None

    def is_allowed(self, ident):
        if self.ident_regex is None:
            return True
        else:
            return bool(self.ident_regex.match(ident))


class CacheNamer(object):
    """
    Provides the name of objects stored in the cache based on their identifier.
    """

    @staticmethod
    def ident_cache_name(ident):
        """
        Returns the name of the individual cache directory for this object.
        """
        # This exists for back-compatibility reasons -- the MD5 hash works
        # just as well on a quoted as unquoted string -- but an old version
        # of this code quoted the string, and we want to preserve existing
        # cache paths.
        ident = quote_plus(ident)

        # Get the MD5 hash of the identifier, then we create the top-level
        # directory as 2 digits, and take pieces of 3 digits for each
        # subsequent directory.
        #
        # For example, '12345678' becomes '12/345/678'.
        #
        ident_hash = hashlib.md5(ident.encode('utf8')).hexdigest()

        dirnames = [ident_hash[0:2]] + [ident_hash[i:i+3] for i in range(2, len(ident_hash), 3)]
        return os.path.join(*tuple(dirnames))

    @staticmethod
    def cache_directory_name(ident):
        """
        Returns the name of the cache directory for this ident, relative
        to the cache root.
        """
        # Split our potential PID spaces.  Fedora Commons is the most likely
        # use case.
        if not ident.startswith(('http://', 'https://')) and len(ident.split(':')) > 1:
            cache_subroot = os.path.join(*tuple(ident.split(':')[:-1]))
        elif ident.startswith(('http://', 'https://')):
            cache_subroot = 'http'
        else:
            cache_subroot = ''

        if cache_subroot:
            return os.path.join(cache_subroot, CacheNamer.ident_cache_name(ident))
        else:
            return CacheNamer.ident_cache_name(ident)
