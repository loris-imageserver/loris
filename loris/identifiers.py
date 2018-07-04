# -*- encoding: utf-8
"""
Utilities for dealing with identifiers.
"""

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
