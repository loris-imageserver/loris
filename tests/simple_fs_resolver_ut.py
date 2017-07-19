from __future__ import absolute_import

import os
import unittest

from loris import resolver
from tests.abstract_resolver import AbstractResolverTest


class SimpleFSResolverTest(AbstractResolverTest, unittest.TestCase):
    TEST_DIR = os.path.dirname(os.path.realpath(__file__))

    def setUp(self):
        super(SimpleFSResolverTest, self).setUp()
        self.img_dir = os.path.join(self.TEST_DIR, 'img')

        single_config = {
            'src_img_root': self.img_dir,
        }

        self.identifier = '01/02/0001.jp2'
        self.not_identifier = 'DOES_NOT_EXIST.jp2'
        self.expected_filepath = os.path.join(
                self.img_dir,
                self.identifier
                )
        self.expected_format = 'jp2'

        self.resolver = resolver.SimpleFSResolver(single_config)


class ExtensionNormalizingFSResolverTest(SimpleFSResolverTest):
    '''The ExtensionNormalizingFSResolver is deprecated - see note in loris/resolvers.py.'''

    def setUp(self):
        super(ExtensionNormalizingFSResolverTest, self).setUp()
        single_config = {
            'src_img_root': self.img_dir,
        }
        self.resolver = resolver.ExtensionNormalizingFSResolver(single_config)


class MultiSourceSimpleFSResolverTest(SimpleFSResolverTest):

    def setUp(self):
        super(MultiSourceSimpleFSResolverTest, self).setUp()
        img_dir = os.path.join(self.TEST_DIR, 'img')
        img_dir2 = os.path.join(self.TEST_DIR, 'img2')

        multiple_config = {
            'src_img_roots': [img_dir2, img_dir]
        }
        self.resolver = resolver.SimpleFSResolver(multiple_config)


def suite():
    test_suites = []
    test_suites.append(
            unittest.makeSuite(SimpleFSResolverTest, 'test')
    )
    test_suites.append(
            unittest.makeSuite(ExtensionNormalizingFSResolverTest, 'test')
    )
    test_suites.append(
            unittest.makeSuite(MultiSourceSimpleFSResolverTest, 'test')
    )
    return unittest.TestSuite(test_suites)


if __name__ == '__main__':
        unittest.main()
