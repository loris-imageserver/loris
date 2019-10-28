import copy
import json
import os
from os.path import dirname
from os.path import isfile
from os.path import join
from os.path import realpath
from os.path import exists
import tempfile
import unittest
from urllib.parse import quote_plus, unquote

import pytest
import responses

from loris.loris_exception import ResolverException
from loris.resolver import (
    _AbstractResolver,
    SimpleHTTPResolver,
    TemplateHTTPResolver,
    SourceImageCachingResolver,
    SimpleFSResolver
)
from tests import loris_t


check_options_test_cases = [
    ({'cert': '/home/cert.pem'}, {'verify': True}),
    ({'cert': '/home/cert.pem', 'key': '/home/key.pem'},
     {'cert': ('/home/cert.pem', '/home/key.pem'), 'verify': True}),
    ({'user': 'loris'}, {'verify': True}),
    ({'user': 'loris', 'pw': 'l3mur'},
     {'auth': ('loris', 'l3mur'), 'verify': True}),
    ({'cert': '/home/cert.pem', 'key': '/home/key.pem', 'user': 'loris', 'pw': 'l3mur'},
     {'cert': ('/home/cert.pem', '/home/key.pem'), 'auth': ('loris', 'l3mur'), 'verify': True}),
    ({'ssl_check': True}, {'verify': True}),
    ({'ssl_check': False}, {'verify': False}),
]


class Test_AbstractResolver(unittest.TestCase):

    def test_format_from_ident(self):
        self.assertEqual(_AbstractResolver(None).format_from_ident('001.JPG'), 'jpg')
        self.assertEqual(_AbstractResolver(None).format_from_ident('001.jpeg'), 'jpg')
        self.assertEqual(_AbstractResolver(None).format_from_ident('001.tiff'), 'tif')
        self.assertEqual(_AbstractResolver(None).format_from_ident('datastreams/master.tiff'), 'tif')
        with self.assertRaises(ResolverException):
            _AbstractResolver(None).format_from_ident('datastream/content')
        with self.assertRaises(ResolverException):
            _AbstractResolver(None).format_from_ident('datastream/content.master')

    def test_is_resolvable_is_notimplementederror(self):
        resolver = _AbstractResolver(None)
        with pytest.raises(NotImplementedError):
            resolver.is_resolvable('001.jpg')

    def test_resolve_is_notimplementederror(self):
        resolver = _AbstractResolver(None)
        with pytest.raises(NotImplementedError):
            resolver.resolve(app=None, ident='001.jpg', base_uri='example.org')


class Test_SimpleFSResolver(loris_t.LorisTest):

    def test_configured_resolver(self):
        expected_path = self.test_jp2_color_fp
        ii = self.app.resolver.resolve(self.app, self.test_jp2_color_id, "")
        self.assertEqual(expected_path, ii.src_img_fp)
        self.assertEqual(ii.src_format, 'jp2')
        self.assertTrue(isfile(ii.src_img_fp))

    def test_multiple_cache_roots(self):
        config = {
            'src_img_roots' : [self.test_img_dir2, self.test_img_dir]
        }
        self.app.resolver = SimpleFSResolver(config)

        ii = self.app.resolver.resolve(self.app, self.test_png_id, "")
        self.assertEqual(self.test_png_fp2, ii.src_img_fp)

        ii2 = self.app.resolver.resolve(self.app, self.test_altpng_id, "")
        self.assertEqual(self.test_altpng_fp, ii2.src_img_fp)

    def test_present_ident_is_resolvable(self):
        ident = self.test_png_id
        config = {
            'src_img_roots' : [self.test_img_dir]
        }
        resolver = SimpleFSResolver(config=config)
        assert resolver.is_resolvable(ident=ident)

    def test_absent_ident_is_unresolvable(self):
        config = {
            'src_img_roots' : ['/var/loris/img']
        }
        resolver = SimpleFSResolver(config=config)
        assert not resolver.is_resolvable(ident='doesnotexist.jpg')

    def test_get_extra_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            ident = 'HP.2007.13.jp2'
            rules_filename = 'HP.2007.13.rules.json'
            source_fp = os.path.join(tmp, ident)
            with open(source_fp, 'wb') as f:
                pass
            with open(os.path.join(tmp, rules_filename), 'wb') as f:
                f.write(json.dumps({'rule': 1}).encode('utf8'))
            config = {
                'src_img_roots' : [tmp]
            }
            resolver = SimpleFSResolver(config=config)
            assert resolver.get_extra_info(ident, source_fp) == {'rule': 1}


class Test_SourceImageCachingResolver(loris_t.LorisTest):

    def test_source_image_caching_resolver(self):
        # First we need to change the resolver on the test instance of the
        # application (overrides the config to use SimpleFSResolver)
        config = {
            'source_root' : join(dirname(realpath(__file__)), 'img'),
            'cache_root' : self.app.img_cache.cache_root
        }
        self.app.resolver = SourceImageCachingResolver(config)

        # Now...
        ident = self.test_jp2_color_id
        ii = self.app.resolver.resolve(self.app, ident, "")
        expected_path = join(self.app.img_cache.cache_root, unquote(ident))

        self.assertEqual(expected_path, ii.src_img_fp)
        self.assertEqual(ii.src_format, 'jp2')
        self.assertTrue(isfile(ii.src_img_fp))

        # Now we resolve it a second time, to test the case where the
        # cache is already warm.
        ii = self.app.resolver.resolve(self.app, ident, base_uri="")
        assert ii.src_img_fp == expected_path
        assert ii.src_format == "jp2"
        assert os.path.isfile(ii.src_img_fp)

    def test_present_ident_is_resolvable(self):
        ident = self.test_png_id
        config = {
            'source_root' : join(dirname(realpath(__file__)), 'img'),
            'cache_root' : self.app.img_cache.cache_root
        }
        resolver = SourceImageCachingResolver(config=config)
        assert resolver.is_resolvable(ident=ident)

    def test_absent_ident_is_unresolvable(self):
        config = {
            'source_root' : '/var/loris/src',
            'cache_root' : '/var/loris/cache'
        }
        resolver = SourceImageCachingResolver(config=config)
        assert not resolver.is_resolvable(ident='doesnotexist.jp2')


@pytest.fixture
def mock_responses():
    with open('tests/img/01/04/0001.tif', 'rb') as f:
        responses.add(
            responses.GET, 'http://sample.sample/0001',
            body=f.read(),
            status=200,
            content_type='image/tiff'
        )

    responses.add(
        responses.HEAD, 'http://sample.sample/0001',
        status=200,
        content_type='image/tiff'
    )

    with open('tests/img/01/04/0001.tif', 'rb') as f:
        responses.add(
            responses.GET, 'http://sample.sample/0002',
            body=f.read(),
            status=200
        )

    body = (
        'II*\x00\x0c\x00\x00\x00\x80\x00  \x0e\x00\x00\x01\x03\x00\x01\x00\x00'
        '\x00\x01\x00\x00\x00\x01\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00'
        '\x02\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x03\x01\x03\x00\x01'
        '\x00\x00\x00\x05\x00\x00\x00\x06\x01\x03\x00\x01\x00\x00\x00\x03\x00'
        '\x00\x00\x11\x01\x04\x00\x01\x00\x00\x00\x08\x00\x00\x00\x15\x01\x03'
        '\x00\x01\x00\x00\x00\x01\x00\x00\x00\x16\x01\x03\x00\x01\x00\x00\x00'
        '\x08\x00\x00\x00\x17\x01\x04\x00\x01\x00\x00\x00\x04\x00\x00\x00\x1a'
        '\x01\x05\x00\x01\x00\x00\x00\xba\x00\x00\x00\x1b\x01\x05\x00\x01\x00'
        '\x00\x00\xc2\x00\x00\x00\x1c\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00'
        '\x00(\x01\x03\x00\x01\x00\x00\x00\x02\x00\x00\x00@\x01\x03\x00\x00'
        '\x03\x00\x00\xca\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x00\x00\x00'
        '\x01\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00\xff`\xe6q\x19\x08\x00'
        '\x00\x80\t\x00\x00\x80\n\x00\x00\x80\x0b\x00\x00\x80\x0c\x00\x00\x80'
        '\r'
    )

    responses.add(
        responses.GET, 'http://sample.sample/0003',
        body=body,
        status=200,
        content_type='image/invalidformat'
    )

    responses.add(
        responses.GET, 'http://sample.sample/DOESNOTEXIST',
        body='Does Not Exist',
        status=404,
        content_type='application/html'
    )


class Test_SimpleHTTPResolver(loris_t.LorisTest):

    def _mock_urls(self):
        mock_responses()

    @responses.activate
    def test_simple_http_resolver(self):

        self._mock_urls()

        # First we test with no config...
        config = {
        }
        self.assertRaises(ResolverException, lambda: SimpleHTTPResolver(config))

        # Then we test missing source_prefix and uri_resolvable
        config = {
            'cache_root' : self.SRC_IMAGE_CACHE
        }
        self.assertRaises(ResolverException, lambda: SimpleHTTPResolver(config))

        # Then we test with the full config...
        #TODO: More granular testing of these settings...
        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'source_prefix' : 'http://www.mysite/',
            'source_suffix' : '/accessMaster',
            'default_format' : 'jp2',
            'head_resolvable' : True,
            'uri_resolvable' : True,
            'user' : 'TestUser',
            'pw' : 'TestPW',
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.source_prefix, 'http://www.mysite/')
        self.assertEqual(self.app.resolver.source_suffix, '/accessMaster')
        self.assertEqual(self.app.resolver.default_format, 'jp2')
        self.assertEqual(self.app.resolver.head_resolvable, True)
        self.assertEqual(self.app.resolver.uri_resolvable, True)
        self.assertEqual(self.app.resolver.user, 'TestUser')
        self.assertEqual(self.app.resolver.pw, 'TestPW')

        # Then we test with a barebones default config...
        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'uri_resolvable' : True
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.source_prefix, '')
        self.assertEqual(self.app.resolver.source_suffix, '')
        self.assertEqual(self.app.resolver.default_format, None)
        self.assertEqual(self.app.resolver.head_resolvable, False)
        self.assertEqual(self.app.resolver.uri_resolvable, True)
        self.assertEqual(self.app.resolver.user, None)
        self.assertEqual(self.app.resolver.pw, None)

        # Finally with the test config for now....
        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'head_resolvable' : True,
            'uri_resolvable' : True
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.source_prefix, 'http://sample.sample/')
        self.assertEqual(self.app.resolver.source_suffix, '')
        self.assertEqual(self.app.resolver.default_format, None)
        self.assertEqual(self.app.resolver.head_resolvable, True)
        self.assertEqual(self.app.resolver.uri_resolvable, True)

        #Test with identifier only
        ident = '0001'
        expected_path = join(self.app.resolver.cache_root, '25')
        expected_path = join(expected_path, 'bbd')
        expected_path = join(expected_path, 'cd0')
        expected_path = join(expected_path, '6c3')
        expected_path = join(expected_path, '2d4')
        expected_path = join(expected_path, '77f')
        expected_path = join(expected_path, '7fa')
        expected_path = join(expected_path, '1c3')
        expected_path = join(expected_path, 'e4a')
        expected_path = join(expected_path, '91b')
        expected_path = join(expected_path, '032')
        expected_path = join(expected_path, '0001') #add identifier to the path
        expected_path = join(expected_path, 'loris_cache.tif')

        ii = self.app.resolver.resolve(self.app, ident, "")
        self.assertEqual(expected_path, ii.src_img_fp)
        self.assertEqual(ii.src_format, 'tif')
        self.assertTrue(isfile(ii.src_img_fp))

        # Now we resolve the same identifier a second time, when the cache
        # is warm.
        ii = self.app.resolver.resolve(self.app, ident, base_uri="")
        assert ii.src_img_fp == expected_path
        assert ii.src_format == "tif"
        assert os.path.isfile(ii.src_img_fp)

        #Test with a full uri
        ident = quote_plus('http://sample.sample/0001')
        expected_path = join(self.app.resolver.cache_root, 'http')
        expected_path = join(expected_path, '32')
        expected_path = join(expected_path, '3a5')
        expected_path = join(expected_path, '353')
        expected_path = join(expected_path, '8f5')
        expected_path = join(expected_path, '0de')
        expected_path = join(expected_path, '1d3')
        expected_path = join(expected_path, '011')
        expected_path = join(expected_path, '675')
        expected_path = join(expected_path, 'ebc')
        expected_path = join(expected_path, 'c75')
        expected_path = join(expected_path, '083')
        expected_path = join(expected_path, unquote(ident))
        expected_path = join(expected_path, 'loris_cache.tif')

        self.assertFalse(exists(expected_path))
        ii = self.app.resolver.resolve(self.app, ident, "")
        self.assertEqual(expected_path, ii.src_img_fp)
        self.assertEqual(ii.src_format, 'tif')
        self.assertTrue(isfile(ii.src_img_fp))

        #Test with a bad identifier
        ident = 'DOESNOTEXIST'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(self.app, ident, ""))

        #Test with a bad url
        ident = quote_plus('http://sample.sample/DOESNOTEXIST')
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(self.app, ident, ""))

        #Test with no content-type or extension or default format
        ident = '0002'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(self.app, ident, ""))

        #Test with invalid content-type
        ident = '0003'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(self.app, ident, ""))

    @responses.activate
    def test_with_default_format(self):
        self._mock_urls()
        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'default_format' : 'tif',
            'head_resolvable' : True,
            'uri_resolvable' : True
        }
        self.app.resolver = SimpleHTTPResolver(config)

        ident = '0002'
        ii = self.app.resolver.resolve(self.app, ident, "")
        self.assertIsNotNone(ii.src_img_fp)
        self.assertEqual(ii.src_format, 'tif')
        self.assertTrue(isfile(ii.src_img_fp))

    @responses.activate
    def test_is_resolvable_uses_cached_result(self):
        self._mock_urls()

        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'default_format' : 'tif',
            'head_resolvable' : True,
            'uri_resolvable' : True
        }
        self.app.resolver = SimpleHTTPResolver(config)

        assert self.app.resolver.resolve(self.app, ident='0001', base_uri='')
        assert self.app.resolver.is_resolvable(ident='0001')

    @responses.activate
    def test_without_extra_info(self):
        self._mock_urls()

        config = {
            'cache_root' : self.SRC_IMAGE_CACHE,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'default_format' : 'tif',
            'head_resolvable' : True,
            'uri_resolvable' : True,
            'use_extra_info' : False
        }
        self.app.resolver = SimpleHTTPResolver(config)

        assert self.app.resolver.resolve(self.app, ident='0001', base_uri='')
        assert self.app.resolver.is_resolvable(ident='0001')


class TestSimpleHTTPResolver(object):

    @pytest.mark.parametrize('config, expected_options',
                             check_options_test_cases)
    def test_request_options_self(self, config, expected_options):
        # Uninteresting for this test, but required so we have a
        # valid config set
        config['cache_root'] = '/var/cache/loris'
        config['uri_resolvable'] = True

        resolver = SimpleHTTPResolver(config)
        assert resolver.request_options() == expected_options

    @responses.activate
    @pytest.mark.parametrize('head_resolvable', [True, False])
    @pytest.mark.parametrize('ident, expected_resolvable', [
        ('0001', True),
        ('0004', False),
        ('doesnotexist.png', False),
    ])
    def test_is_resolvable(self, mock_responses,
                           head_resolvable, ident, expected_resolvable):
        config = {
            'cache_root': '/var/cache/loris',
            'source_prefix': 'http://sample.sample/',
            'uri_resolvable': True,
            'head_resolvable': head_resolvable,
        }
        resolver = SimpleHTTPResolver(config=config)
        assert resolver.is_resolvable(ident=ident) == expected_resolvable

    @pytest.mark.parametrize('head_resolvable', [True, False])
    def test_non_http_rejected_as_not_resolvable(self, head_resolvable):
        config = {
            'cache_root': '/var/cache/loris',
            'source_prefix': 'irc://example.irc/loris/',
            'uri_resolvable': True,
            'head_resolvable': head_resolvable,
        }
        resolver = SimpleHTTPResolver(config=config)
        assert not resolver.is_resolvable(ident='example.png')

    @responses.activate
    @pytest.mark.parametrize('ident_regex, ident, expected_resolvable', [
        ('A+', 'bbb.jpg', False),
        ('\d+', '0001', True),
        ('\d+Z', '0001', False),
    ])
    def test_ident_regex_blocks_based_on_ident(self, mock_responses, ident_regex, ident, expected_resolvable):
        config = {
            'cache_root': '/var/cache/loris',
            'source_prefix': 'http://sample.sample/',
            'ident_regex': ident_regex,
        }
        resolver = SimpleHTTPResolver(config=config)
        assert resolver.is_resolvable(ident=ident) == expected_resolvable


class Test_TemplateHTTPResolver(object):

    config = {
        'cache_root' : '/var/cache/loris',
        'templates': 'a, b, c, d, sample',
        'a': {
            'url': 'http://mysite.com/images/%s'
        },
        'b': {
            'url': 'http://mysite.com/images/%s/access/'
        },
        'c': {
            'url': 'http://othersite.co/img/%s'
        },
        'sample': {
            'url': 'http://sample.sample/%s'
        }
    }

    def test_template_http_resolver_with_no_config_is_error(self):
        with pytest.raises(ResolverException):
            TemplateHTTPResolver({})

    def test_allow_no_template_config(self):
        no_template_config = {
            k: v for k, v in self.config.items() if k != "templates"
        }
        resolver = TemplateHTTPResolver(no_template_config)

        with pytest.raises(ResolverException):
            resolver.resolve(app=None, ident="a:foo.jpg", base_uri="")

    def test_parsing_template_http_resolver_config(self):
        resolver = TemplateHTTPResolver(self.config)
        assert resolver.cache_root == self.config['cache_root']

        assert resolver.templates['a'] == self.config['a']
        assert resolver.templates['b'] == self.config['b']
        assert resolver.templates['c'] == self.config['c']
        assert 'd' not in resolver.templates

        # Automatically set by SimpleHTTPResolver
        assert resolver.uri_resolvable

    @pytest.mark.parametrize('ident, expected_uri', [
        ('a:foo.jpg', 'http://mysite.com/images/foo.jpg'),
        ('b:id1', 'http://mysite.com/images/id1/access/'),
        ('c:foo:bar:baz', 'http://othersite.co/img/foo:bar:baz'),
    ])
    def test_web_request_uri_logic(self, ident, expected_uri):
        resolver = TemplateHTTPResolver(self.config)
        uri, _ = resolver._web_request_url(ident)
        assert uri == expected_uri

    @pytest.mark.parametrize('bad_ident', [
        'foo',
        'unknown:id2',
    ])
    def test_bad_ident_is_resolvererror(self, bad_ident):
        resolver = TemplateHTTPResolver(self.config)
        with pytest.raises(ResolverException) as exc:
            resolver._web_request_url(bad_ident)
        assert 'Bad URL request' in str(exc.value)

    delimited_config = {
        'cache_root' : '/var/cache/loris',
        'templates': 'delim1, delim2',
        'delimiter': '|',
        'delim1': {
            'url': 'http://mysite.com/images/%s/access/%s'
        },
        'delim2': {
            'url': 'http://anothersite.com/img/%s/files/%s/dir/%s'
        }
    }

    @pytest.mark.parametrize('ident, expected_uri', [
        ('delim1:foo|bar', 'http://mysite.com/images/foo/access/bar'),
        ('delim2:red|green|blue', 'http://anothersite.com/img/red/files/green/dir/blue'),
    ])
    def test_using_delimiters_for_template(self, ident, expected_uri):
        resolver = TemplateHTTPResolver(self.delimited_config)
        uri, _ = resolver._web_request_url(ident)
        assert uri == expected_uri

    @pytest.mark.parametrize('bad_ident', [
        'delim1:up|down|left|right',
        'nodelim',
    ])
    def test_bad_delimited_ident_is_resolvererror(self, bad_ident):
        resolver = TemplateHTTPResolver(self.delimited_config)
        with pytest.raises(ResolverException) as exc:
            resolver._web_request_url(bad_ident)
        assert 'Bad URL request' in str(exc.value)

    @pytest.mark.parametrize('config, expected_options',
                             check_options_test_cases)
    def test_adding_options_to_parsed_uri(self, config, expected_options):
        new_config = copy.deepcopy(self.config)
        new_config['a'].update(config)
        resolver = TemplateHTTPResolver(new_config)
        _, options = resolver._web_request_url('a:id1.jpg')
        assert options == expected_options

    @responses.activate
    @pytest.mark.parametrize('ident, expected_resolvable', [
        ('sample:0001', True),
        ('sample:0004', False),
        ('doesnotmatchatemplate', False),
    ])
    def test_is_resolvable(self, mock_responses, ident, expected_resolvable):
        resolver = TemplateHTTPResolver(self.config)
        assert resolver.is_resolvable(ident=ident) == expected_resolvable
