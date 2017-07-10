from loris.resolver import SimpleHTTPResolver
from loris.loris_exception import ResolverException
import os
import shutil
import unittest
import responses


class SimpleHTTPResolverTest(unittest.TestCase):

    def setUp(self):
        super(SimpleHTTPResolverTest, self).setUp()
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_dir = os.path.join(tests_dir, 'cache')
        prefix_url = 'http://sample.sample/'

        config = {
            'cache_root': self.cache_dir,
            'source_prefix': prefix_url,
            'source_suffix': '',
            'head_resolvable': True,
            'uri_resolvable': True
        }
        self.resolver = SimpleHTTPResolver(config)
        self.not_identifier = 'DOES_NOT_EXIST'
        self.not_identifier_url = ''.join(
                [
                    prefix_url,
                    self.not_identifier
                ]
        )
        self.identifier = '0001'
        self.identifier_url = ''.join(
                [
                    prefix_url,
                    self.identifier
                ]
        )
        self.expected_format = 'tif'
        expected_filepath_list = [
                    self.cache_dir,
                    '25',
                    'bbd',
                    'cd0',
                    '6c3',
                    '2d4',
                    '77f',
                    '7fa',
                    '1c3',
                    'e4a',
                    '91b',
                    '032',
                ]
        self.expected_filedir = os.path.join(*expected_filepath_list)
        self.expected_filepath = os.path.join(self.expected_filedir, 'loris_cache.tif')
        self.set_responses()

    def set_responses(self):
        responses.add(
                responses.HEAD,
                self.identifier_url,
                status=200,
                content_type='image/tiff'
        )
        responses.add(
                responses.GET,
                self.identifier_url,
                body='II*\x00\x0c\x00\x00\x00\x80\x00  \x0e\x00\x00\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x03\x01\x03\x00\x01\x00\x00\x00\x05\x00\x00\x00\x06\x01\x03\x00\x01\x00\x00\x00\x03\x00\x00\x00\x11\x01\x04\x00\x01\x00\x00\x00\x08\x00\x00\x00\x15\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x16\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x17\x01\x04\x00\x01\x00\x00\x00\x04\x00\x00\x00\x1a\x01\x05\x00\x01\x00\x00\x00\xba\x00\x00\x00\x1b\x01\x05\x00\x01\x00\x00\x00\xc2\x00\x00\x00\x1c\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00(\x01\x03\x00\x01\x00\x00\x00\x02\x00\x00\x00@\x01\x03\x00\x00\x03\x00\x00\xca\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00\xff`\xe6q\x19\x08\x00\x00\x80\t\x00\x00\x80\n\x00\x00\x80\x0b\x00\x00\x80\x0c\x00\x00\x80\r',
                status=200,
                content_type='image/tiff'
        )
        responses.add(
                responses.HEAD,
                self.not_identifier_url,
                status=404,
                content_type='application/html'
        )
        responses.add(
                responses.GET,
                self.not_identifier_url,
                body='Does Not Exist',
                status=404,
                content_type='application/html'
        )

    def test_get_format(self):
        self.resolver.default_format = 'tif'
        self.assertEqual(self.resolver.get_format('0001.jp2', None), 'tif')
        self.resolver.default_format = None
        self.assertEqual(self.resolver.get_format('0001.jp2', 'tif'), 'tif')
        self.assertEqual(self.resolver.get_format('0001.jp2', None), 'jp2')

    @responses.activate
    def test_bad_url(self):
        self.assertRaises(
                ResolverException,
                lambda: self.resolver.resolve(self.not_identifier_url, "")
        )

    @responses.activate
    def test_does_not_exist(self):
        self.assertRaises(
                ResolverException,
                lambda: self.resolver.resolve(self.not_identifier, "")
        )

    @responses.activate
    def test_cached_file_for_ident(self):
        self.resolver.copy_to_cache(self.identifier)
        self.assertTrue(os.path.isfile(self.expected_filepath))
        self.assertEqual(self.resolver.cached_file_for_ident(self.identifier), self.expected_filepath)

    @responses.activate
    def test_resolve_001(self):
        expected_resolved = self.expected_filepath
        ii = self.resolver.resolve(self.identifier, "")
        self.assertEqual(ii.src_img_fp, expected_resolved)
        # Make sure the file exists in the cache
        self.assertTrue(os.path.isfile(self.expected_filepath))

    @responses.activate
    def test_is_resolvable_001(self):
        self.assertTrue(
         self.resolver.is_resolvable(self.identifier)
        )
        # Make sure the file DOES NOT exists in the cache
        self.assertFalse(os.path.isfile(self.expected_filepath))

    @responses.activate
    def test_is_not_resolvable(self):
        self.assertFalse(
                self.resolver.is_resolvable(self.not_identifier)
        )

    def tearDown(self):
        # Clean Up the cache directory
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)


class SimpleHTTPResolverConfigTest(unittest.TestCase):

    def setUp(self):
        super(SimpleHTTPResolverConfigTest, self).setUp()
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_dir = os.path.join(tests_dir, 'cache')

    def test_no_config(self):
        config = {}
        self.assertRaises(
                ResolverException,
                lambda: SimpleHTTPResolver(config)
        )

    def test_missing_required_config(self):
        config = {
            'cache_root': self.cache_dir
        }
        self.assertRaises(
                ResolverException,
                lambda: SimpleHTTPResolver(config)
        )

    def test_config_assigned_to_resolver(self):
        config = {
            'cache_root': self.cache_dir,
            'source_prefix': 'http://www.mysite/',
            'source_suffix': '/accessMaster',
            'default_format': 'jp2',
            'head_resolvable': True,
            'uri_resolvable': True,
            'user': 'TestUser',
            'pw': 'TestPW',
        }

        resolver = SimpleHTTPResolver(config)
        self.assertEqual(resolver.cache_root, self.cache_dir)
        self.assertEqual(resolver.source_prefix, 'http://www.mysite/')
        self.assertEqual(resolver.source_suffix, '/accessMaster')
        self.assertEqual(resolver.default_format, 'jp2')
        self.assertEqual(resolver.head_resolvable, True)
        self.assertEqual(resolver.uri_resolvable, True)
        self.assertEqual(resolver.user, 'TestUser')
        self.assertEqual(resolver.pw, 'TestPW')

    def test_barebones_config(self):
        config = {
            'cache_root': self.cache_dir,
            'uri_resolvable': True
        }

        resolver = SimpleHTTPResolver(config)
        self.assertEqual(resolver.cache_root, self.cache_dir)
        self.assertEqual(resolver.source_prefix, '')
        self.assertEqual(resolver.source_suffix, '')
        self.assertEqual(resolver.default_format, None)
        self.assertEqual(resolver.head_resolvable, False)
        self.assertEqual(resolver.uri_resolvable, True)
        self.assertEqual(resolver.user, None)
        self.assertEqual(resolver.pw, None)


def suite():
    test_suites = []
    test_suites.append(
            unittest.makeSuite(SimpleHTTPResolverConfigTest, 'test')
    )
    test_suites.append(
            unittest.makeSuite(SimpleHTTPResolverTest, 'test')
    )
    return unittest.TestSuite(test_suites)


if __name__ == '__main__':
        unittest.main()
