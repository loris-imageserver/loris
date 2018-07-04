# -*- encoding: utf-8
"""
Utilities for dealing with identifiers.
"""

import hashlib
import os
import re


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
        Returns the name of the cache directory for this object.
        """
        # Get the MD5 hash of the identifier, then we create the top-level
        # directory as 2 digits, and take pieces of 3 digits for each
        # subsequent directory.
        #
        # For example, '12345678' becomes '12/345/678'.
        #
        ident_hash = hashlib.md5(ident.encode('utf8')).hexdigest()

        dirnames = [ident_hash[0:2]] + [ident_hash[i:i+3] for i in range(2, len(ident_hash), 3)]
        return os.path.join(*tuple(dirnames))
