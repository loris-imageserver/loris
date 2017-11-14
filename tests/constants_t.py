#-*- coding: utf-8 -*-

import pytest

from loris import constants

class TestImageRequest(object):

    def test_valid_filenames(self):
        self._assert_valid('/123.jpg/full/full/0/default.jpg')

    @pytest.mark.parametrize('path', [
        '/a*b/full/full/0/default.jpg',
        '/a:b/full/full/0/default.jpg',
        '/a-b/full/full/0/default.jpg',
        '/a%b/full/full/0/default.jpg'
    ])
    def test_valid_special_characters(self, path):
        self._assert_valid(path)

    def _assert_valid(self, path):
        assert constants.IMAGE_RE.match(path) is not None

