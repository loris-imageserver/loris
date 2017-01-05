#-*- coding: utf-8 -*-
from loris.loris_exception import ResolverException
from loris.resolver import SimpleHTTPResolver, TemplateHTTPResolver
from loris.resolver import SourceImageCachingResolver, SimpleFSResolver
from os.path import dirname
from os.path import isfile
from os.path import join
from os.path import realpath
from os.path import exists
from urllib import unquote, quote_plus

import loris_t
import responses


"""
Resolver tests. This may need to be modified if you change the resolver 
implementation. To run this test on its own, do:

$ python -m unittest tests.resolver_t

from the `/loris` (not `/loris/loris`) directory.
"""

class Test_SimpleFSResolver(loris_t.LorisTest):

    def test_configured_resolver(self):
        expected_path = self.test_jp2_color_fp
        resolved_path, fmt = self.app.resolver.resolve(self.test_jp2_color_id)
        self.assertEqual(expected_path, resolved_path)
        self.assertEqual(fmt, 'jp2')
        self.assertTrue(isfile(resolved_path))

    def test_format_is_lowercase(self):
        resolved_path, fmt = self.app.resolver.resolve('01%2F03%2F0002.JPG')
        self.assertEqual(fmt, 'jpg')

    def test_multiple_cache_roots(self):
        config = {
            'src_img_roots' : [self.test_img_dir2, self.test_img_dir]
        }
        self.app.resolver = SimpleFSResolver(config)

        resolved_path, fmt = self.app.resolver.resolve(self.test_png_id)
        self.assertEqual(self.test_png_fp2, resolved_path)

        resolved_path, fmt = self.app.resolver.resolve(self.test_altpng_id)
        self.assertEqual(self.test_altpng_fp, resolved_path)


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
        resolved_path, fmt = self.app.resolver.resolve(ident)
        expected_path = join(self.app.img_cache.cache_root, unquote(ident))

        self.assertEqual(expected_path, resolved_path)
        self.assertEqual(fmt, 'jp2')
        self.assertTrue(isfile(resolved_path))

class Test_SimpleHTTPResolver(loris_t.LorisTest):

    @responses.activate
    def test_simple_http_resolver(self):

        # Mock out some urls for testing....
        responses.add(responses.GET, 'http://sample.sample/0001',
                      body='II*\x00\x0c\x00\x00\x00\x80\x00  \x0e\x00\x00\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x03\x01\x03\x00\x01\x00\x00\x00\x05\x00\x00\x00\x06\x01\x03\x00\x01\x00\x00\x00\x03\x00\x00\x00\x11\x01\x04\x00\x01\x00\x00\x00\x08\x00\x00\x00\x15\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x16\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x17\x01\x04\x00\x01\x00\x00\x00\x04\x00\x00\x00\x1a\x01\x05\x00\x01\x00\x00\x00\xba\x00\x00\x00\x1b\x01\x05\x00\x01\x00\x00\x00\xc2\x00\x00\x00\x1c\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00(\x01\x03\x00\x01\x00\x00\x00\x02\x00\x00\x00@\x01\x03\x00\x00\x03\x00\x00\xca\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00\xff`\xe6q\x19\x08\x00\x00\x80\t\x00\x00\x80\n\x00\x00\x80\x0b\x00\x00\x80\x0c\x00\x00\x80\r',
                      status=200,
                      content_type='image/tiff')

        responses.add(responses.GET, 'http://sample.sample/0002',
                      body='II*\x00\x0c\x00\x00\x00\x80\x00  \x0e\x00\x00\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x03\x01\x03\x00\x01\x00\x00\x00\x05\x00\x00\x00\x06\x01\x03\x00\x01\x00\x00\x00\x03\x00\x00\x00\x11\x01\x04\x00\x01\x00\x00\x00\x08\x00\x00\x00\x15\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x16\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x17\x01\x04\x00\x01\x00\x00\x00\x04\x00\x00\x00\x1a\x01\x05\x00\x01\x00\x00\x00\xba\x00\x00\x00\x1b\x01\x05\x00\x01\x00\x00\x00\xc2\x00\x00\x00\x1c\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00(\x01\x03\x00\x01\x00\x00\x00\x02\x00\x00\x00@\x01\x03\x00\x00\x03\x00\x00\xca\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00\xff`\xe6q\x19\x08\x00\x00\x80\t\x00\x00\x80\n\x00\x00\x80\x0b\x00\x00\x80\x0c\x00\x00\x80\r',
                      status=200)

        responses.add(responses.GET, 'http://sample.sample/0003',
                      body='II*\x00\x0c\x00\x00\x00\x80\x00  \x0e\x00\x00\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x03\x01\x03\x00\x01\x00\x00\x00\x05\x00\x00\x00\x06\x01\x03\x00\x01\x00\x00\x00\x03\x00\x00\x00\x11\x01\x04\x00\x01\x00\x00\x00\x08\x00\x00\x00\x15\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00\x16\x01\x03\x00\x01\x00\x00\x00\x08\x00\x00\x00\x17\x01\x04\x00\x01\x00\x00\x00\x04\x00\x00\x00\x1a\x01\x05\x00\x01\x00\x00\x00\xba\x00\x00\x00\x1b\x01\x05\x00\x01\x00\x00\x00\xc2\x00\x00\x00\x1c\x01\x03\x00\x01\x00\x00\x00\x01\x00\x00\x00(\x01\x03\x00\x01\x00\x00\x00\x02\x00\x00\x00@\x01\x03\x00\x00\x03\x00\x00\xca\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00H\x00\x00\x00\x01\x00\x00\x00\xff`\xe6q\x19\x08\x00\x00\x80\t\x00\x00\x80\n\x00\x00\x80\x0b\x00\x00\x80\x0c\x00\x00\x80\r',
                      status=200,
                      content_type='image/invalidformat')

        responses.add(responses.GET, 'http://sample.sample/DOESNOTEXIST',
                      body='Does Not Exist',
                      status=404,
                      content_type='application/html')


        # First we test with no config...
        config = {
        }
        self.assertRaises(ResolverException, lambda: SimpleHTTPResolver(config))

        # Then we test missing source_prefix and uri_resolvable
        config = {
            'cache_root' : self.app.img_cache.cache_root
        }
        self.assertRaises(ResolverException, lambda: SimpleHTTPResolver(config))

        # Then we test with the full config...
        #TODO: More granular testing of these settings...
        config = {
            'cache_root' : self.app.img_cache.cache_root,
            'source_prefix' : 'http://www.mysite/',
            'source_suffix' : '/accessMaster',
            'default_format' : 'jp2',
            'head_resolvable' : True,
            'uri_resolvable' : True,
            'user' : 'TestUser',
            'pw' : 'TestPW',
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.cache_root, self.app.img_cache.cache_root)
        self.assertEqual(self.app.resolver.source_prefix, 'http://www.mysite/')
        self.assertEqual(self.app.resolver.source_suffix, '/accessMaster')
        self.assertEqual(self.app.resolver.default_format, 'jp2')
        self.assertEqual(self.app.resolver.head_resolvable, True)
        self.assertEqual(self.app.resolver.uri_resolvable, True)
        self.assertEqual(self.app.resolver.user, 'TestUser')
        self.assertEqual(self.app.resolver.pw, 'TestPW')

        # Then we test with a barebones default config...
        config = {
            'cache_root' : self.app.img_cache.cache_root,
            'uri_resolvable' : True
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.cache_root, self.app.img_cache.cache_root)
        self.assertEqual(self.app.resolver.source_prefix, '')
        self.assertEqual(self.app.resolver.source_suffix, '')
        self.assertEqual(self.app.resolver.default_format, None)
        self.assertEqual(self.app.resolver.head_resolvable, False)
        self.assertEqual(self.app.resolver.uri_resolvable, True)
        self.assertEqual(self.app.resolver.user, None)
        self.assertEqual(self.app.resolver.pw, None)

        # Finally with the test config for now....
        config = {
            'cache_root' : self.app.img_cache.cache_root,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'head_resolvable' : True,
            'uri_resolvable' : True
        }

        self.app.resolver = SimpleHTTPResolver(config)
        self.assertEqual(self.app.resolver.cache_root, self.app.img_cache.cache_root)
        self.assertEqual(self.app.resolver.source_prefix, 'http://sample.sample/')
        self.assertEqual(self.app.resolver.source_suffix, '')
        self.assertEqual(self.app.resolver.default_format, None)
        self.assertEqual(self.app.resolver.head_resolvable, True)
        self.assertEqual(self.app.resolver.uri_resolvable, True)

        #Test with identifier only
        ident = '0001'
        expected_path = join(self.app.img_cache.cache_root, '25')
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
        expected_path = join(expected_path, 'loris_cache.tif')

        resolved_path, fmt = self.app.resolver.resolve(ident)
        self.assertEqual(expected_path, resolved_path)
        self.assertEqual(fmt, 'tif')
        self.assertTrue(isfile(resolved_path))

        #Test with a full uri
        #Note: This seems weird but idents resolve wrong and removes a slash from //
        ident = quote_plus('http://sample.sample/0001')
        expected_path = join(self.app.img_cache.cache_root, 'http')
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
        expected_path = join(expected_path, 'loris_cache.tif')

        self.assertFalse(exists(expected_path))
        self.assertFalse(self.app.resolver.in_cache(ident))
        resolved_path, fmt = self.app.resolver.resolve(ident)
        self.assertEqual(expected_path, resolved_path)
        self.assertEqual(fmt, 'tif')
        self.assertTrue(isfile(resolved_path))
        self.assertTrue(self.app.resolver.in_cache(ident))

        #Test with a bad identifier
        ident = 'DOESNOTEXIST'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(ident))

        #Test with a bad url
        ident = quote_plus('http://sample.sample/DOESNOTEXIST')
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(ident))

        #Test with no content-type or extension or default format
        ident = '0002'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(ident))

        #Test with invalid content-type
        ident = '0003'
        self.assertRaises(ResolverException, lambda: self.app.resolver.resolve(ident))

        #Tests with a default format...
        config = {
            'cache_root' : self.app.img_cache.cache_root,
            'source_prefix' : 'http://sample.sample/',
            'source_suffix' : '',
            'default_format' : 'tif',
            'head_resolvable' : True,
            'uri_resolvable' : True
        }
        self.app.resolver = SimpleHTTPResolver(config)

        ident = '0002'
        resolved_path, fmt = self.app.resolver.resolve(ident)
        self.assertIsNotNone(resolved_path)
        self.assertEqual(fmt, 'tif')
        self.assertTrue(isfile(resolved_path))

        ident = '0003'
        resolved_path, fmt = self.app.resolver.resolve(ident)
        self.assertIsNotNone(resolved_path)
        self.assertEqual(fmt, 'tif')
        self.assertTrue(isfile(resolved_path))


class Test_TemplateHTTPResolver(loris_t.LorisTest):

    def test_template_http_resolver(self):

        # Test with no config
        self.assertRaises(ResolverException,
            lambda: TemplateHTTPResolver({}))

        # Test with the multiple templates
        config = {
            'cache_root' : self.app.img_cache.cache_root,
            'templates': 'a,b, c, d',
            'a': {
                'url': 'http://mysite.com/images/%s'
            },
            'b': {
                'url': 'http://mysite.com/images/%s/access/'
            },
            'c': {
                'url': 'http://othersite.co/img/%s'
            }
        }

        self.app.resolver = TemplateHTTPResolver(config)
        self.assertEqual(self.app.resolver.cache_root, self.app.img_cache.cache_root)
        self.assert_('a' in self.app.resolver.templates)
        self.assert_('b' in self.app.resolver.templates)
        self.assert_('c' in self.app.resolver.templates)
        self.assert_('d' not in self.app.resolver.templates)
        self.assertEqual(self.app.resolver.templates['a'],
            config['a'])
        self.assertEqual(self.app.resolver.templates['b'],
            config['b'])
        self.assertEqual(self.app.resolver.templates['c'],
            config['c'])
        # automatically set for simple http resolver
        self.assertEqual(self.app.resolver.uri_resolvable, True)

        # test web request uri logic
        self.assertEqual('http://mysite.com/images/foo.jpg',
            self.app.resolver._web_request_url('a:foo.jpg')[0])
        self.assertEqual('http://mysite.com/images/id1/access/',
            self.app.resolver._web_request_url('b:id1')[0])
        self.assertEqual('http://othersite.co/img/foo:bar:baz',
            self.app.resolver._web_request_url('c:foo:bar:baz')[0])
        self.assertEqual(None,
            self.app.resolver._web_request_url('unknown:id2')[0])


def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_SimpleFSResolver, 'test'))
    test_suites.append(unittest.makeSuite(Test_SourceImageCachingResolver, 'test'))
    test_suites.append(unittest.makeSuite(Test_SimpleHTTPResolver, 'test'))
    test_suites.append(unittest.makeSuite(Test_TemplateHTTPResolver, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
