from __future__ import absolute_import

import os
import unittest

import botocore
from mock import patch, MagicMock

from img_info import ImageInfo
from loris.resolver import MultipleResolver, _AbstractResolver
from loris.loris_exception import ResolverException


class MockResolver(_AbstractResolver):

    def __init__(self, config):
        super(MockResolver, self).__init__(config)
        self.resolves = config.get('resolves')

    def is_resolvable(self, ident):
        return self.resolves

    def resolve(self, app, ident, base_uri):
        if self.resolves:
            return ImageInfo(app, ident, src_img_fp="example.jpg", src_format="jpeg")


class MultipleResolverTest(unittest.TestCase):

    @staticmethod
    def build_resolver_config(resolves):
        return {'impl': 'tests.multiple_resolver_t.MockResolver', 'resolves': resolves}

    def setUp(self):
        super(MultipleResolverTest, self).setUp()
        self.ident = '0001'

        self.unresolvable = MultipleResolver({'resolvers': ['Mock1', 'Mock2'],
                                              'Mock1': self.build_resolver_config(False),
                                              'Mock2': self.build_resolver_config(False)})
        self.resolvable_by_first = MultipleResolver({'resolvers': ['Mock1', 'Mock2'],
                                                     'Mock1': self.build_resolver_config(True),
                                                     'Mock2': self.build_resolver_config(False)})
        self.resolvable_by_last = MultipleResolver({'resolvers': ['Mock1', 'Mock2', 'Mock3'],
                                                    'Mock1': self.build_resolver_config(False),
                                                    'Mock2': self.build_resolver_config(False),
                                                    'Mock3': self.build_resolver_config(True)})

    def test_not_resolvers_can_resolve(self):
        self.assertFalse(self.unresolvable.is_resolvable(self.ident))

    def test_resolvable_by_first_resolver(self):
        self.assertTrue(self.resolvable_by_first.is_resolvable(self.ident))

    def test_resolvable_by_last_resolver(self):
        self.assertTrue(self.resolvable_by_last.is_resolvable(self.ident))

    def test_is_resolvable_001(self):
        pass


class MultipleResolverConfigTest(unittest.TestCase):

    def setUp(self):
        super(MultipleResolverConfigTest, self).setUp()

    def test_no_config(self):
        config = {}
        self.assertRaises(
                ResolverException,
                lambda: MultipleResolver(config)
        )

    def test_only_one_resolver(self):
        config = {
            'resolvers': ['Mock1']
        }
        self.assertRaises(
                ResolverException,
                lambda: MultipleResolver(config)
        )

    def test_config_assigned_to_resolver(self):
        resolver = MultipleResolver({'resolvers': ['Mock1', 'Mock2'],
                                     'Mock1': MultipleResolverTest.build_resolver_config(True),
                                     'Mock2': MultipleResolverTest.build_resolver_config(False)})
        self.assertEqual(len(resolver.resolvers), 2)
