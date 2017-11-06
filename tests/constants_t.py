#-*- coding: utf-8 -*-

import unittest

from loris import constants

class TestImageRequest(unittest.TestCase):

    def test_valid_filenames(self):
        self._assert_valid('/123.jpg/full/full/0/default.jpg')

    def test_valid_special_characters(self):
        self._assert_valid('/a*b/full/full/0/default.jpg')
        self._assert_valid('/a:b/full/full/0/default.jpg')
        self._assert_valid('/a-b/full/full/0/default.jpg')
        self._assert_valid('/a%b/full/full/0/default.jpg')

    def _assert_valid(self, path):
        self.assertIsNotNone(constants.IMAGE_RE.match(path))

