# -*- encoding: utf-8

from hypothesis import given
from hypothesis.strategies import text
import pytest

from loris.identifiers import IdentRegexChecker


class TestIdentRegexChecker(object):

    @given(text(min_size=1))
    def test_any_ident_is_allowed_if_regex_is_none(self, ident):
        checker = IdentRegexChecker(ident_regex=None)
        assert checker.is_allowed(ident=ident) is True

    @pytest.mark.parametrize('ident_regex, ident, expected_is_allowed', [
        (r'^A+$', 'AAAA', True),
        (r'^A+$', 'AAAB', False),
        (r'[0-9]+\.jpg', '001.jpg', True),
        (r'[0-9]+\.jpg', '001.tif', False),
    ])
    def test_checker_has_correct_is_allowed(
        self, ident_regex, ident, expected_is_allowed
    ):
        checker = IdentRegexChecker(ident_regex=ident_regex)
        assert checker.is_allowed(ident=ident) is expected_is_allowed
