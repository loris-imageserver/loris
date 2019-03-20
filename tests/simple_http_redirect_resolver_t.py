from __future__ import absolute_import

import os
import unittest

from mock import patch, MagicMock

from loris.resolver import SimpleHTTPRedirectResolver
from loris.loris_exception import ResolverException


class SimpleHTTPRedirectResolverTest(unittest.TestCase):

    def setUp(self):
        super(SimpleHTTPRedirectResolverTest, self).setUp()
        self.prefix_url = 'http://sample.sample/'

        config = {
            'source_prefix': self.prefix_url,
        }
        self.resolver = SimpleHTTPRedirectResolver(config)
        self.not_identifier = 'DOES_NOT_EXIST'
        self.identifier = '0001'

    @patch('loris.resolver.requests')
    def test_resolve_001(self, req):
        req.get.return_value = MagicMock(status_code=200)
        ii = self.resolver.resolve(None, self.identifier, "")
        self.assertEquals(ii.redirect_url, self.prefix_url)

    @patch('loris.resolver.requests')
    def test_is_resolvable_001(self, req):
        req.get.return_value = MagicMock(status_code=200)
        self.assertTrue(
         self.resolver.is_resolvable(self.identifier)
        )

    @patch('loris.resolver.requests')
    def test_is_not_resolvable(self, req):
        req.get.return_value = MagicMock(status_code=404)
        self.assertFalse(
                self.resolver.is_resolvable(self.not_identifier)
        )


class SimpleHTTPRedirectResolverConfigTest(unittest.TestCase):

    def setUp(self):
        super(SimpleHTTPRedirectResolverConfigTest, self).setUp()
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_dir = os.path.join(tests_dir, 'cache')

    def test_no_config(self):
        config = {}
        self.assertRaises(
                ResolverException,
                lambda: SimpleHTTPRedirectResolver(config)
        )

    def test_missing_required_config(self):
        config = {
            'cache_root': self.cache_dir
        }
        self.assertRaises(
                ResolverException,
                lambda: SimpleHTTPRedirectResolver(config)
        )

    def test_config_assigned_to_resolver(self):
        config = {
            'source_prefix': 'http://www.mysite/',
        }

        resolver = SimpleHTTPRedirectResolver(config)
        self.assertEqual(resolver.source_prefix, 'http://www.mysite/')
