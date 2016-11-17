# webapp_t.py
#-*- coding: utf-8 -*-

from datetime import datetime
from os import path, listdir
from time import sleep
from unittest import TestCase
from werkzeug.datastructures import Headers
from werkzeug.http import http_date
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
import re
import loris_t
from loris import img_info
from loris import webapp


"""
Webapp tests. To run this test on its own, do:

$ python -m unittest -v tests.webapp_t

from the `/loris` (not `/loris/loris`) directory.
"""
class TestBaseUri(loris_t.LorisTest):

    def test_get_base_uri(self):
        path = '/%s/' % self.test_jp2_color_id
        builder = EnvironBuilder(path=path)
        env = builder.get_environ()
        req = Request(env)
        base_uri = self.app._get_base_uri(req, self.test_jp2_color_id)
        self.assertEqual(base_uri, 'http://localhost/01%2F02%2F0001.jp2')

    def test_get_base_uri_proxy_path(self):
        path = '/%s/' % self.test_jp2_color_id
        builder = EnvironBuilder(path=path)
        env = builder.get_environ()
        req = Request(env)
        self.app.proxy_path = 'http://example.org/'
        base_uri = self.app._get_base_uri(req, self.test_jp2_color_id)
        self.assertEqual(base_uri, 'http://example.org/01%2F02%2F0001.jp2')


class TestDissectUri(TestCase):

    def setUp(self):
        self.test_jp2_color_id = '01%2F02%2F0001.jp2'

    def test_root_path(self):
        path = '/'
        uri_dissector = webapp.URIDissector(path, True)
        self.assertEqual(uri_dissector.ident, '')
        self.assertEqual(uri_dissector.params, '')
        self.assertEqual(uri_dissector.request_type, 'index')

    def test_favicon(self):
        path = '/favicon.ico'
        uri_dissector = webapp.URIDissector(path, True)
        self.assertEqual(uri_dissector.ident, '')
        self.assertEqual(uri_dissector.params, '')
        self.assertEqual(uri_dissector.request_type, 'favicon')

    def test_unescaped_ident_request(self):
        path = '/01/02/0001.jp2/'
        uri_dissector = webapp.URIDissector(path, True)
        self.assertEqual(uri_dissector.ident, '01%2F02%2F0001.jp2')
        self.assertEqual(uri_dissector.params, '')
        self.assertEqual(uri_dissector.request_type, 'redirect_info')

    def test_ident_request(self):
        path = '/%s/' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(path, True)
        self.assertEqual(uri_dissector.ident, self.test_jp2_color_id)
        self.assertEqual(uri_dissector.params, '')
        self.assertEqual(uri_dissector.request_type, 'redirect_info')

    def test_ident_request_no_redirect(self):
        path = '/%s/' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(path, False)
        self.assertEqual(uri_dissector.ident, self.test_jp2_color_id + '%2F')
        self.assertEqual(uri_dissector.request_type, 'redirect_info')

    def test_info_request(self):
        info_path = '/%s/%s' % (self.test_jp2_color_id,'info.json')
        uri_dissector = webapp.URIDissector(info_path, True)
        self.assertEqual(uri_dissector.ident, self.test_jp2_color_id)
        self.assertEqual(uri_dissector.params, 'info.json')
        self.assertEqual(uri_dissector.request_type, 'info')

    def test_img_request(self):
        img_path = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.ident, self.test_jp2_color_id)
        expected_params = {'region': u'full', 'size': u'full', 'rotation': u'0', 'quality': u'default', 'format': u'jpg'}
        self.assertEqual(uri_dissector.params, expected_params)
        self.assertEqual(uri_dissector.request_type, u'image')

    def test_img_region(self):
        img_path = '/%s/square/full/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['region'], 'square')
        img_path = '/%s/0,0,500,500/full/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['region'], '0,0,500,500')
        img_path = '/%s/pct:41.6,7.5,40,70/full/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['region'], 'pct:41.6,7.5,40,70')

    def test_img_size(self):
        img_path = '/%s/full/full/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['size'], 'full')
        img_path = '/%s/full/max/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['size'], 'max')
        img_path = '/%s/full/150,/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['size'], '150,')
        img_path = '/%s/full/pct:50/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['size'], 'pct:50')
        img_path = '/%s/full/!225,100/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['size'], '!225,100')

    def test_img_rotation(self):
        img_path = '/%s/full/full/0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['rotation'], '0')
        img_path = '/%s/full/full/22.5/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['rotation'], '22.5')
        img_path = '/%s/full/full/!0/default.jpg' % self.test_jp2_color_id
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'image')
        self.assertEqual(uri_dissector.params['rotation'], '!0')

    def test_img_quality(self):
        img_path = '/%s/full/full/0/gray.jpg' % (self.test_jp2_color_id,)
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, 'image')
        self.assertEqual(uri_dissector.params['quality'], 'gray')
        img_path = '/%s/full/full/0/native.jpg' % (self.test_jp2_color_id,)
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, u'bad_image_request')

    def test_img_format(self):
        img_path = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.request_type, 'image')
        self.assertEqual(uri_dissector.params['format'], 'jpg')

    def test_many_slash_img_request(self):
        identifier = '1/2/3/4/5/6/7/8/9/xyz'
        encoded_identifier = '1%2F2%2F3%2F4%2F5%2F6%2F7%2F8%2F9%2Fxyz'
        img_path = '/%s/full/full/0/default.jpg' % identifier
        uri_dissector = webapp.URIDissector(img_path, True)
        self.assertEqual(uri_dissector.ident, encoded_identifier)
        expected_params = {'region': u'full', 'size': u'full', 'rotation': u'0', 'quality': u'default', 'format': u'jpg'}
        self.assertEqual(uri_dissector.params, expected_params)
        self.assertEqual(uri_dissector.request_type, u'image')

    def test_many_slash_info_request(self):
        identifier = '1/2/3/4/5/6/7/8/9/xyz'
        encoded_identifier = '1%2F2%2F3%2F4%2F5%2F6%2F7%2F8%2F9%2Fxyz'
        info_path = '/%s/info.json' % identifier
        uri_dissector = webapp.URIDissector(info_path, True)
        self.assertEqual(uri_dissector.request_type, u'info')
        self.assertEqual(uri_dissector.ident, encoded_identifier)


class WebappIntegration(loris_t.LorisTest):
    'Simulate working with the webapp over HTTP.'

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.startswith('This is Loris, '))

    def test_favicon(self):
        resp = self.client.get('/favicon.ico')
        self.assertEqual(resp.status_code, 200)

    def test_bare_identifier_request_303(self):
        resp = self.client.get('/%s' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp.headers['Location'], 'http://localhost/01%2F02%2F0001.jp2/info.json')

    def test_bare_identifier_request_with_trailing_slash_303(self):
        resp = self.client.get('/%s/' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp.headers['Location'], 'http://localhost/01%2F02%2F0001.jp2/info.json')

    def test_bare_identifier_with_trailing_slash_404s_with_redir_off(self):
        self.app.redirect_id_slash_to_info = False
        resp = self.client.get('/%s/' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 404)

    def test_access_control_allow_origin_on_bare_identifier(self):
        resp = self.client.get('/%s' % (self.test_jp2_color_id,), follow_redirects=False)
        self.assertEqual(resp.headers['access-control-allow-origin'], '*')

    def test_access_control_allow_origin_on_info_requests(self):
        uri = '/%s/info.json' % (self.test_jp2_color_id,)
        resp = self.client.get(uri)
        self.assertEqual(resp.headers['access-control-allow-origin'], '*')

    def test_access_control_allow_origin_on_img_request(self):
        uri = '/%s/full/100,/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(uri)
        self.assertEqual(resp.headers['access-control-allow-origin'], '*')

    def test_cors_regex_match(self):
        self.app.cors_regex = re.compile('calhos')
        to_get = '/%s/full/110,/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEquals(resp.headers['Access-Control-Allow-Origin'], 'http://localhost/')

    def test_cors_regex_no_match(self):
        self.app.cors_regex = re.compile('fooxyz')
        to_get = '/%s/full/120,/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertFalse(resp.headers.has_key('Access-Control-Allow-Origin'))

    def test_bare_broken_identifier_request_404(self):
        resp = self.client.get('/foo%2Fbar')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers['content-type'], 'text/plain')

    def test_info_not_found_request(self):
        resp = self.client.get('/foobar/info.json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers['content-type'], 'text/plain')

    def test_image_not_found_request(self):
        resp = self.client.get('/foobar/full/full/0/default.jpg')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers['content-type'], 'text/plain')

    def test_bare_identifier_request_303_gets_info(self):
        # Follow the redirect. After that this is nearly a copy of
        # img_info_t.C_InfoFunctionalTests#test_jp2_info_dot_json_request
        to_get = '/%s' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'application/json')

        tmp_fp = path.join(self.app.tmp_dp, 'loris_test_info.json')
        with open(tmp_fp, 'wb') as f:
            f.write(resp.data)

        info = img_info.ImageInfo.from_json(tmp_fp)
        self.assertEqual(info.width, self.test_jp2_color_dims[0])

    def test_info_without_dot_json_404(self):
        # Note that this isn't what we really want...should be 400, but this
        # gets through as an ID. Technically OK, I think.
        to_get = '/%s/info' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 404)

    def test_image_without_format_400(self):
        to_get = '/%s/full/full/0/default' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_image_redirect_to_canonical(self):
        self.app.redirect_canonical_image_request = True
        to_get = '/%s/0,0,500,600/!550,600/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get, follow_redirects=False)
        self.assertEqual(resp.status_code, 301)

    def test_image_no_redirect_to_canonical(self):
        self.app.redirect_canonical_image_request = False
        to_get = '/%s/0,0,500,600/!550,600/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get, follow_redirects=False)
        self.assertEqual(resp.status_code, 200)

    def test_img_sends_304(self):
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)

        # get an image
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 200)
        lmod =  resp.headers['Last-Modified']

        sleep(1) # just make sure.
        headers = Headers([('If-Modified-Since', lmod)])
        resp = self.client.get(to_get, headers=headers)
        self.assertEqual(resp.status_code, 304)

        sleep(1)
        dt = http_date(datetime.utcnow()) # ~2 seconds later
        headers = Headers([('If-Modified-Since', dt)])
        resp = self.client.get(to_get, headers=headers)
        self.assertEqual(resp.status_code, 304)

    def test_img_reduce(self):
        to_get = '/%s/full/300,/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 200)


    def test_no_ims_header_ok(self):
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        # get an image
        resp = self.client.get(to_get, headers=Headers())
        self.assertEqual(resp.status_code, 200)

    def test_info_fake_jp2(self):
        to_get = '/01%2F03%2Ffake.jp2/info.json'
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data, 'Server Side Error: Invalid JP2 file (500)')

    def test_info_sends_304(self):
        to_get = '/%s/info.json' % (self.test_jp2_color_id,)

        # get an image
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 200)
        lmod = resp.headers['Last-Modified']

        sleep(1) # just make sure.
        headers = Headers([('if-modified-since', lmod)])
        resp = self.client.get(to_get, headers=headers)
        self.assertEqual(resp.status_code, 304)

        sleep(1)
        dt = http_date(datetime.utcnow()) # ~2 seconds later
        headers = Headers([('if-modified-since', dt)])
        resp = self.client.get(to_get, headers=headers)
        self.assertEqual(resp.status_code, 304)

    def test_bad_format_returns_400(self):
        to_get = '/%s/full/full/0/default.hey' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_bad_quality_returns_400(self):
        to_get = '/%s/full/full/0/native.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_bad_quality_for_gray_image_returns_400(self):
        to_get = '/%s/full/full/0/color.jpg' % (self.test_jp2_gray_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_bad_rotation_returns_400(self):
        to_get = '/%s/full/full/x/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_bad_size_returns_400(self):
        to_get = '/%s/full/xyz/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_bad_region_returns_400(self):
        to_get = '/%s/foo_/full/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        self.assertEqual(resp.status_code, 400)

    def test_cleans_up_when_not_caching(self):
        self.app.enable_caching = False
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get)
        # callback should delete the image before the test ends, so the tmp dir
        # should not contain any files (there may be dirs)
        tmp = self.app.tmp_dp
        any_files = any([path.isfile(path.join(tmp, n)) for n in listdir(tmp)])
        self.assertTrue(not any_files)


class SizeRestriction(loris_t.LorisTest):
    '''Tests for restriction of size parameter.'''

    def setUp(self):
        '''Set max_size_above_full to 100 for tests.'''
        super(SizeRestriction, self).setUp()
        self.app.max_size_above_full = 100

    def test_json_no_size_above_full(self):
        '''Is 'sizeAboveFull' removed from json?'''
        request_path = '/%s/info.json' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse('sizeAboveFull' in resp.data)

    def _test_json_has_size_above_full(self):
        '''Does sizeAboveFull remain in info.json if size > 100?'''
        self.app.max_size_above_full = 200
        request_path = '/%s/info.json' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('sizeAboveFull' in resp.data)


    def test_full_full(self):
        '''full/full has no size restrictions.'''
        request_path = '/%s/full/full/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

    def test_percent_ok(self):
        '''pct:100 is allowed.'''
        request_path = '/%s/full/pct:100/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

    def test_percent_ok_200(self):
        '''pct:200 is allowed is max_size_above_full is 200.'''
        self.app.max_size_above_full = 200
        request_path = '/%s/full/pct:200/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

    def test_percent_exceeds_100(self):
        '''Restrict interpolation. So pct:101 must be rejected.'''
        request_path = '/%s/full/pct:101/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 404)

    def test_percent_exceeds_200(self):
        '''Restrict interpolation to 200. So pct:201 must be rejected.'''
        self.app.max_size_above_full = 200
        request_path = '/%s/full/pct:201/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 404)

    def test_size_width_ok(self):
        '''Explicit width in size parameter is not larger than image size.'''
        request_path = '/%s/full/3600,/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

    def test_size_width_too_big(self):
        '''Explicit width in size parameter is larger than image size.'''
        request_path = '/%s/full/3601,/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 404)

    def test_size_height_ok(self):
        '''Explicit height in size parameter is not larger than image height.'''
        request_path = '/%s/full/,2987/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

    def test_size_height_to_big(self):
        '''Explicit height in size parameter is larger than image height.'''
        request_path = '/%s/full/,2988/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 404)

    def test_region_too_big(self):
        '''It's not allowed to make a region larger than 100% of original
        region size.'''
        request_path = '/%s/100,100,100,100/120,/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 404)


    def test_no_restriction(self):
        '''If max_size_above_full ist set to 0, users can request
        any image size.'''
        self.app.max_size_above_full = 0
        request_path = '/%s/full/pct:120/0/default.jpg' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)


def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(TestBaseUri, 'test'))
    test_suites.append(unittest.makeSuite(TestDissectUri, 'test'))
    test_suites.append(unittest.makeSuite(WebappIntegration, 'test'))
    test_suites.append(unittest.makeSuite(SizeRestriction, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
