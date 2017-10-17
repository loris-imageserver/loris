from __future__ import absolute_import

import os
import shutil
import unittest

from tests.abstract_resolver import AbstractResolverTest
from loris import resolver


class SourceImageCachingResolverTest(AbstractResolverTest, unittest.TestCase):

    def setUp(self):
        super(SourceImageCachingResolverTest, self).setUp()
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_dir = os.path.join(tests_dir, 'cache')
        config = {
            'source_root': os.path.join(tests_dir, 'img'),
            'cache_root': self.cache_dir
        }

        self.identifier = '01/02/0001.jp2'
        self.expected_filepath = os.path.join(
                self.cache_dir,
                self.identifier
        )
        self.not_identifier = 'DOES_NOT_EXIST.jp2'
        self.expected_format = 'jp2'

        self.resolver = resolver.SourceImageCachingResolver(config)

    def test_resolve(self):
        super(SourceImageCachingResolverTest, self).test_resolve()

        # Make sure the file exists in the cache
        self.assertTrue(os.path.isfile(self.expected_filepath))

    def tearDown(self):
        # Clean Up the cache directory
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
