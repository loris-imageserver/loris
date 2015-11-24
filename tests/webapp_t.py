# webapp_t.py
#-*- coding: utf-8 -*-

from datetime import datetime
from loris import img_info
from loris import constants
from loris import webapp
from os import path, listdir
from time import sleep
from werkzeug.datastructures import Headers
from werkzeug.http import parse_date, http_date
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
import json
import loris_t


"""
Webapp tests. To run this test on its own, do:

$ python -m unittest -v tests.webapp_t

from the `/loris` (not `/loris/loris`) directory.
"""

class Test_E_WebappUnit(loris_t.LorisTest):
    def test_uri_from_info_request(self):
        info_path = '/%s/%s' % (self.test_jp2_color_id,'info.json')

        # See http://werkzeug.pocoo.org/docs/test/#environment-building
        builder = EnvironBuilder(path=info_path)
        env = builder.get_environ()
        req = Request(env)

        base_uri, ident, params, request_type = self.app._dissect_uri(req)
        expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
        self.assertEqual(base_uri, expected)

    def test_uri_from_img_request(self):
        img_path = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)

        builder = EnvironBuilder(path=img_path)
        env = builder.get_environ()
        req = Request(env)

        base_uri, ident, params, request_type = self.app._dissect_uri(req)
        expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
        self.assertEqual(base_uri, expected)
    

class Test_F_WebappFunctional(loris_t.LorisTest):
    'Simulate working with the webapp over HTTP.'

    def test_bare_identifier_request_303(self):
        resp = self.client.get('/%s' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 303)

    def test_bare_identifier_request_with_trailing_slash_303(self):
        resp = self.client.get('/%s/' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 303)

    def test_bare_identifier_with_trailing_slash_404s_with_redir_off(self):
        self.app.redirect_id_slash_to_info = False
        resp = self.client.get('/%s/' % (self.test_jp2_color_id,))
        self.assertEqual(resp.status_code, 404)

    def test_access_control_allow_origin_on_info_requests(self):
        uri = '/%s/info.json' % (self.test_jp2_color_id,)
        resp = self.client.get(uri)
        self.assertEqual(resp.headers['access-control-allow-origin'], '*')

    def test_access_control_allow_origin_on_img_request(self):
        uri = '/%s/full/full/0/default.jpg' % (self.test_jp2_color_id,)
        resp = self.client.get(uri)
        self.assertEqual(resp.headers['access-control-allow-origin'], '*')

    def test_bare_broken_identifier_request_404(self):
        resp = self.client.get('/foo%2Fbar')
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


def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_E_WebappUnit, 'test'))
    test_suites.append(unittest.makeSuite(Test_F_WebappFunctional, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
