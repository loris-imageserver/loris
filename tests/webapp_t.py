# webapp_t.py
#-*- coding: utf-8 -*-

from __future__ import absolute_import

from datetime import datetime
from os import path, listdir
from time import sleep
from unittest import TestCase
import re

import pytest
from werkzeug.datastructures import Headers
from werkzeug.http import http_date
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from loris import img_info, webapp
from loris.loris_exception import ConfigError
from loris.transforms import KakaduJP2Transformer, OPJ_JP2Transformer
from tests import loris_t


def _get_werkzeug_request(path):
    builder = EnvironBuilder(path=path)
    env = builder.get_environ()
    return Request(env)


class TestDebugConfig(object):
    def test_debug_config_gives_kakadu_transformer(self):
        config = webapp.get_debug_config('kdu')
        app = webapp.Loris(config)
        assert isinstance(app.transformers['jp2'], KakaduJP2Transformer)

    def test_debug_config_gives_openjpeg_transformer(self):
        config = webapp.get_debug_config('opj')
        app = webapp.Loris(config)
        assert isinstance(app.transformers['jp2'], OPJ_JP2Transformer)

    def test_unrecognized_debug_config_is_configerror(self):
        with pytest.raises(ConfigError) as err:
            webapp.get_debug_config('no_such_jp2_transformer')
        assert 'Unrecognized debug JP2 transformer' in str(err.value)


class TestLorisRequest(TestCase):

    def setUp(self):
        self.test_jp2_color_id = '01%2F02%2F0001.jp2'

    def test_get_base_uri(self):
        path = '/%s/' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, True, None)
        self.assertEqual(loris_request.base_uri, 'http://localhost/01%2F02%2F0001.jp2')

    def test_get_base_uri_proxy_path(self):
        path = '/%s/' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        proxy_path = 'http://example.org/'
        loris_request = webapp.LorisRequest(req, True, proxy_path)
        self.assertEqual(loris_request.base_uri, 'http://example.org/01%2F02%2F0001.jp2')

    def test_root_path(self):
        path = '/'
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, '')
        self.assertEqual(loris_request.params, '')
        self.assertEqual(loris_request.request_type, 'index')

    def test_favicon(self):
        path = '/favicon.ico'
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, '')
        self.assertEqual(loris_request.params, '')
        self.assertEqual(loris_request.request_type, 'favicon')

    def test_unescaped_ident_request(self):
        path = '/01/02/0001.jp2/'
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, True, None)
        self.assertEqual(loris_request.ident, '01%2F02%2F0001.jp2')
        self.assertEqual(loris_request.params, '')
        self.assertEqual(loris_request.request_type, 'redirect_info')

    def test_ident_request(self):
        path = '/%s/' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, True, None)
        self.assertEqual(loris_request.ident, self.test_jp2_color_id)
        self.assertEqual(loris_request.params, '')
        self.assertEqual(loris_request.request_type, 'redirect_info')

    def test_ident_request_no_redirect(self):
        path = '/%s/' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, self.test_jp2_color_id + '%2F')
        self.assertEqual(loris_request.request_type, 'redirect_info')

    def test_info_request(self):
        info_path = '/%s/info.json' % self.test_jp2_color_id
        req = _get_werkzeug_request(info_path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, self.test_jp2_color_id)
        self.assertEqual(loris_request.params, 'info.json')
        self.assertEqual(loris_request.request_type, 'info')

    def test_img_request(self):
        path = '/%s/full/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, self.test_jp2_color_id)
        expected_params = {'region': u'full', 'size': u'full', 'rotation': u'0', 'quality': u'default', 'format': u'jpg'}
        self.assertEqual(loris_request.params, expected_params)
        self.assertEqual(loris_request.request_type, u'image')

    def test_img_region(self):
        path = '/%s/square/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['region'], 'square')
        path = '/%s/0,0,500,500/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['region'], '0,0,500,500')
        path = '/%s/pct:41.6,7.5,40,70/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['region'], 'pct:41.6,7.5,40,70')

    def test_img_size(self):
        path = '/%s/full/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['size'], 'full')
        path = '/%s/full/max/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['size'], 'max')
        path = '/%s/full/150,/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['size'], '150,')
        path = '/%s/full/pct:50/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['size'], 'pct:50')
        path = '/%s/full/!225,100/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['size'], '!225,100')

    def test_img_rotation(self):
        path = '/%s/full/full/0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['rotation'], '0')
        path = '/%s/full/full/22.5/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['rotation'], '22.5')
        path = '/%s/full/full/!0/default.jpg' % self.test_jp2_color_id
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.params['rotation'], '!0')

    def test_img_quality(self):
        path = '/%s/full/full/0/gray.jpg' % (self.test_jp2_color_id,)
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, 'image')
        self.assertEqual(loris_request.params['quality'], 'gray')
        path = '/%s/full/full/0/native.jpg' % (self.test_jp2_color_id,)
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'bad_image_request')

    def test_img_format(self):
        path = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, 'image')
        self.assertEqual(loris_request.params['format'], 'jpg')

    def test_many_slash_img_request(self):
        identifier = '1/2/3/4/5/6/7/8/9/xyz'
        encoded_identifier = '1%2F2%2F3%2F4%2F5%2F6%2F7%2F8%2F9%2Fxyz'
        path = '/%s/full/full/0/default.jpg' % identifier
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, encoded_identifier)
        expected_params = {'region': u'full', 'size': u'full', 'rotation': u'0', 'quality': u'default', 'format': u'jpg'}
        self.assertEqual(loris_request.params, expected_params)
        self.assertEqual(loris_request.request_type, u'image')

    def test_https_uri_identifier(self):
        identifier = 'https://sample.sample/0001'
        encoded_identifier = 'https%3A%2F%2Fsample.sample%2F0001'
        path = '/%s/full/full/0/default.jpg' % identifier
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.ident, encoded_identifier)
        expected_params = {'region': u'full', 'size': u'full', 'rotation': u'0', 'quality': u'default', 'format': u'jpg'}
        self.assertEqual(loris_request.params, expected_params)
        self.assertEqual(loris_request.request_type, u'image')

    def test_many_slash_info_request(self):
        identifier = '1/2/3/4/5/6/7/8/9/xyz'
        encoded_identifier = '1%2F2%2F3%2F4%2F5%2F6%2F7%2F8%2F9%2Fxyz'
        path = '/%s/info.json' % identifier
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req, False, None)
        self.assertEqual(loris_request.request_type, u'info')
        self.assertEqual(loris_request.ident, encoded_identifier)

    def test_template_delimiter_request(self):
        identifier = u'a:foo|bar'
        encoded_identifier = u'a%3Afoo%7Cbar'
        #image request
        path = u'/%s/full/full/0/default.jpg' % identifier
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req)
        self.assertEqual(loris_request.request_type, u'image')
        self.assertEqual(loris_request.ident, encoded_identifier)
        #info request
        path = u'/%s/info.json' % identifier
        req = _get_werkzeug_request(path)
        loris_request = webapp.LorisRequest(req)
        self.assertEqual(loris_request.request_type, u'info')
        self.assertEqual(loris_request.ident, encoded_identifier)


class TestGetInfo(loris_t.LorisTest):

    def test_get_info(self):
        path = '/%s/' % self.test_jp2_color_id
        req = _get_werkzeug_request(path=path)
        base_uri = 'http://example.org/01%2F02%2F0001.jp2'
        info, last_mod = self.app._get_info(self.test_jp2_color_id, req, base_uri)
        self.assertEqual(info.ident, base_uri)

    def test_get_info_invalid_src_format(self):
        # This functionality was factored out
        # --azaroth42 2017-07-07
        return None
        #path = '/%s/' % self.test_jp2_color_id
        #builder = EnvironBuilder(path=path)
        #env = builder.get_environ()
        #req = Request(env)
        #base_uri = 'http://example.org/01%2F02%2F0001.jp2'
        #src_fp = 'invalid'
        #src_format = 'invalid'
        #exception = loris_exception.ImageInfoException
        #function = self.app._get_info
        #args = [self.test_jp2_color_id, req, base_uri]
        #self.assertRaises(exception, function, *args)



class WebappIntegration(loris_t.LorisTest):
    'Simulate working with the webapp over HTTP.'

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.decode('utf8').startswith('This is Loris, '))

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

        info = img_info.ImageInfo.from_json_fp(tmp_fp)
        self.assertEqual(info.width, self.test_jp2_color_dims[0])

    def test_gif_identifier(self):
        # Should be able to request source GIF in a supported target format
        # Note: cannot use @pytest.mark.parametrize here because this is a unittest.TestCase subclass
        for target_format in ( 'gif', 'jpg', 'png', 'webp'):
            identifier = 'three_static.gif'
            to_get = '/%s/full/full/0/default.%s' % (identifier, target_format)
            resp = self.client.get(to_get)
            self.assertEqual(resp.status_code, 200)

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

    def test_image_proxy_path_canonical_link(self):
        self.app.proxy_path = 'https://proxy_example.org/image/'
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get, follow_redirects=False)
        self.assertEqual(resp.status_code, 200)
        link = '<http://iiif.io/api/image/2/level2.json>;rel="profile",<https://proxy_example.org/image/01%2F02%2F0001.jp2/full/full/0/default.jpg>;rel="canonical"'
        self.assertEqual(resp.headers['Link'], link)

    def test_image_canonical_link(self):
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(to_get, follow_redirects=False)
        self.assertEqual(resp.status_code, 200)
        link = '<http://iiif.io/api/image/2/level2.json>;rel="profile",<http://localhost/01%2F02%2F0001.jp2/full/full/0/default.jpg>;rel="canonical"'
        self.assertEqual(resp.headers['Link'], link)

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
        self.assertEqual(resp.data.decode('utf8'), 'Server Side Error: Invalid JP2 file (500)')

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

    def test_info_with_callback_is_wrapped_correctly(self):
        to_get = '/%s/info.json?callback=mycallback' % self.test_jpeg_id
        resp = self.client.get(to_get)
        assert resp.status_code == 200

        assert re.match(r'^mycallback\(.*\);$', resp.data.decode('utf8'))

    def test_info_as_options(self):
        to_opt = '/%s/info.json?callback=mycallback' % self.test_jpeg_id
        resp = self.client.options(to_opt)
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Methods') == 'GET, OPTIONS'

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

    def test_cleans_up_when_caching(self):
        self.app.enable_caching = True
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        # We use the response as a context manager to ensure it gets
        # closed before the test ends.
        with self.client.get(to_get):
            pass
        self._assert_tmp_has_no_files()

    def test_cleans_up_when_not_caching(self):
        self.app.enable_caching = False
        to_get = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        # We use the response as a context manager to ensure it gets
        # closed before the test ends.
        with self.client.get(to_get):
            pass
        self._assert_tmp_has_no_files()

    def _assert_tmp_has_no_files(self):
        # callback should delete the image before the test ends, so the tmp dir
        # should not contain any files (there may be dirs)
        tmp = self.app.tmp_dp
        any_files = any([path.isfile(path.join(tmp, n)) for n in listdir(tmp)])
        self.assertTrue(not any_files, "There are too many files in %s: %s" % (tmp, any_files))



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
        self.assertFalse('sizeAboveFull' in resp.data.decode('utf8'))

    def _test_json_has_size_above_full(self):
        '''Does sizeAboveFull remain in info.json if size > 100?'''
        self.app.max_size_above_full = 200
        request_path = '/%s/info.json' % (self.test_jpeg_id,)
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('sizeAboveFull' in resp.data.decode('utf8'))


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
