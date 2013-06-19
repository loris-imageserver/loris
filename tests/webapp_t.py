# webapp_t.py
#-*- coding: utf-8 -*-

from loris import img_info
from loris import webapp
from os import path
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
from werkzeug.datastructures import Headers
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

		uri = webapp.Loris._base_uri_from_request(req)
		expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
		self.assertEqual(uri, expected)

	def test_uri_from_img_request(self):
		img_path = '/%s/full/full/0/native.jpg' % (self.test_jp2_color_id,)

		builder = EnvironBuilder(path=img_path)
		env = builder.get_environ()
		req = Request(env)

		uri = webapp.Loris._base_uri_from_request(req)
		expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
		self.assertEqual(uri, expected)

class Test_F_WebappFunctional(loris_t.LorisTest):
	'Simulate working with the webapp over HTTP.'

	def test_bare_identifier_request_303(self):
		resp = self.client.get('/%s' % (self.test_jp2_color_id,))
		self.assertEqual(resp.status_code, 303)

	def test_bare_identifier_request_without_303_enabled(self):
		# disable the redirect
		self.app.redirect_base_uri = False
		resp = self.client.get('/%s' % (self.test_jp2_color_id,))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.headers['content-type'], 'application/json')

		tmp_fp = path.join(self.app.tmp_dp, 'loris_test_info.json')
		with open(tmp_fp, 'wb') as f:
			f.write(resp.data)

		info = img_info.ImageInfo.from_json(tmp_fp)
		self.assertEqual(info.width, self.test_jp2_color_dims[0])

	def test_bare_identifier_request_404(self):
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

	# conneg with redirect
	def test_info_conneg_does_redirect(self):
		to_get = '/%s/info' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=False)
		self.assertEqual(resp.status_code, 301)

	def test_info_conneg_gets_info_after_redirect(self):
		to_get = '/%s/info' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=True)
		self.assertEqual(resp.status_code, 200)

		tmp_fp = path.join(self.app.tmp_dp, 'loris_test_info.json')
		with open(tmp_fp, 'wb') as f:
			f.write(resp.data)

		info = img_info.ImageInfo.from_json(tmp_fp)
		self.assertEqual(info.width, self.test_jp2_color_dims[0])

	def test_info_conneg_does_not_redirect_and_returns_info(self):
		self.app.redirect_conneg = False
		to_get = '/%s/info' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=True)
		self.assertEqual(resp.status_code, 200)

		tmp_fp = path.join(self.app.tmp_dp, 'loris_test_info.json')
		with open(tmp_fp, 'wb') as f:
			f.write(resp.data)

		info = img_info.ImageInfo.from_json(tmp_fp)
		self.assertEqual(info.width, self.test_jp2_color_dims[0])

	def test_info_conneg_415(self):
		self.app.redirect_conneg = False
		h = Headers()
		h.add('accept','text/plain')
		to_get = '/%s/info' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, headers=h, follow_redirects=True)
		self.assertEqual(resp.status_code, 415)


	def test_image_conneg_redirect(self):
		self.app.redirect_conneg = True
		h = Headers()
		h.add('accept','image/jpeg')
		to_get = '/%s/full/full/0/native' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, headers=h, follow_redirects=False)
		self.assertEqual(resp.status_code, 301)


	def test_image_redirect_to_cannonical(self):
		self.app.redirect_cannonical_image_request = True
		to_get = '/%s/0,0,500,600/!550,600/0/native.jpg' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=False)
		self.assertEqual(resp.status_code, 301)

	def test_image_no_redirect_to_cannonical(self):
		self.app.redirect_cannonical_image_request = False
		to_get = '/%s/0,0,500,600/!550,600/0/native.jpg' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=False)
		self.assertEqual(resp.status_code, 200)


def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(Test_E_WebappUnit, 'test'))
	test_suites.append(unittest.makeSuite(Test_F_WebappFunctional, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite