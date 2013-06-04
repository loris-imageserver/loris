# webapp_t.py
#-*- coding: utf-8 -*-

from loris import img_info
from loris import webapp
from os import path
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
import json
import loris_t


"""
Webapp tests. To run this test on its own, do:

$ python -m unittest -v tests.webapp_t

from the `/loris` (not `/loris/loris`) directory.
"""

class E_WebappUnitTests(loris_t.LorisTest):
	def test_uri_from_info_request(self):
		# We're testing a private method here, but this is complex
		# enough that it's warranted.
		info_path = '/%s/%s' % (self.test_jp2_color_id,'info.json')

		# See http://werkzeug.pocoo.org/docs/test/#environment-building
		builder = EnvironBuilder(path=info_path)
		env = builder.get_environ()
		req = Request(env)

		uri = webapp.Loris._Loris__uri_from_request(req)
		expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
		self.assertEqual(uri, expected)

	def test_uri_from_img_request(self):
		img_path = '/%s/full/full/0/native.jpg' % (self.test_jp2_color_id,)

		builder = EnvironBuilder(path=img_path)
		env = builder.get_environ()
		req = Request(env)

		uri = webapp.Loris._Loris__uri_from_request(req)
		expected = '/'.join((self.URI_BASE, self.test_jp2_color_id))
		self.assertEqual(uri, expected)

class F_WebappFunctionalTests(loris_t.LorisTest):
	'Simulate working with the webapp over HTTP.'

	def test_bare_identifier_request_303(self):
		resp = self.client.get('/%s' % (self.test_jp2_color_id,))
		self.assertEqual(resp.status_code, 303)

	def test_bare_identifier_request_404(self):
		resp = self.client.get('/foo%2Fbar')
		self.assertEqual(resp.status_code, 404)
		self.assertEqual(resp.headers['content-type'], 'text/plain')

	def test_bare_identifier_request_gets_info(self):
		# Follow the redirect. After that this is nearly a copy of 
		# img_info_t.C_InfoFunctionalTests#test_jp2_info_dot_json_request
		to_get = '/%s' % (self.test_jp2_color_id,)
		resp = self.client.get(to_get, follow_redirects=True)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.headers['content-type'], 'application/json')

		tmp_fp = path.join(self.app.config['loris.Loris']['tmp_dp'], 'loris_test_info.json')
		with open(tmp_fp, 'wb') as f:
			f.write(resp.data)

		info = img_info.ImageInfo.from_json(tmp_fp)
		self.assertEqual(info.width, self.test_jp2_color_dims[0])
		self.assertEqual(info.height, self.test_jp2_color_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey','color'])
		self.assertEqual(info.tile_width, self.test_jp2_color_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_color_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16])

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(E_WebappUnitTests, 'test'))
	test_suites.append(unittest.makeSuite(F_WebappFunctionalTests, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite