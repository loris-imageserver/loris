from __future__ import absolute_import

import os
import unittest

import botocore
from mock import patch, MagicMock

from loris.resolver import SimpleHTTPRedirectResolver, SimpleS3Resolver
from loris.loris_exception import ResolverException


class SimpleS3ResolverTest(unittest.TestCase):

    def setUp(self):
        super(SimpleS3ResolverTest, self).setUp()
        self.s3_path = 's3://bucket/prefix'
        self.cache_root = '/tmp/cache'

        config = {
            's3_path': self.s3_path,
            'cache_root': self.cache_root
        }
        self.resolver = SimpleS3Resolver(config)
        self.not_identifier = 'DOES_NOT_EXIST'
        self.identifier = '0001'

    @patch('loris.resolver.boto3')
    def test_resolve_001(self, boto):
        s3 = MagicMock()
        boto.client.return_value = s3
        s3.download_file.return_value = 'tests/img/67352ccc-d1b0-11e1-89ae-279075081939.jp2'
        ii = self.resolver.resolve(None, 'test.jp2', "")
        self.assertEqual('/tmp/cache/18/a29/789/d9d/b01/da2/f5b/644/3a8/4c1/193/loris_cache.jp2', ii.src_img_fp)

    @patch('loris.resolver.boto3')
    def test_is_resolvable_001(self, boto):
        s3 = MagicMock()
        obj = MagicMock()
        boto.resource.return_value = s3
        s3.Object.return_value = obj
        self.assertTrue(
         self.resolver.is_resolvable(self.identifier)
        )

    @patch('loris.resolver.boto3')
    def test_is_not_resolvable(self, boto):
        s3 = MagicMock()
        obj = MagicMock()
        boto.resource.return_value = s3
        s3.Object.return_value = obj
        obj.load.side_effect = botocore.exceptions.ClientError({}, {})
        self.assertFalse(
                self.resolver.is_resolvable(self.not_identifier)
        )


class SimpleS3ResolverConfigTest(unittest.TestCase):

    def setUp(self):
        super(SimpleS3ResolverConfigTest, self).setUp()
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_dir = os.path.join(tests_dir, 'cache')

    def test_no_config(self):
        config = {}
        self.assertRaises(
                ResolverException,
                lambda: SimpleS3Resolver(config)
        )

    def test_missing_required_config(self):
        config = {
            'cache_root': self.cache_dir
        }
        self.assertRaises(
                ResolverException,
                lambda: SimpleS3Resolver(config)
        )

    def test_must_have_s3_prefix(self):
        config = {
            'cache_root': self.cache_dir,
            's3_path': '/invalid/path'
        }
        self.assertRaises(
                ResolverException,
                lambda: SimpleS3Resolver(config)
        )

    def test_config_assigned_to_resolver(self):
        config = {
            'cache_root': self.cache_dir,
            's3_path': 's3://bucket/path/prefix/',
        }

        resolver = SimpleS3Resolver(config)
        self.assertEqual(resolver.s3bucket, 'bucket')
        self.assertEqual(resolver.prefix, 'path/prefix/')
