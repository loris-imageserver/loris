# webapp_t.py
#-*- coding: utf-8 -*-

from loris import img_info
from os import path
import json
import loris_t

"""
Webapp tests. To run this test on its own, do:

$ python -m unittest -v tests.webapp_t

from the `/loris` (not `/loris/loris`) directory.
"""

class E_WebappFunctionalTests(loris_t.LorisTest):
	'Simulate working with the webapp over HTTP.'

	def test_bare_identifier_request_303(self):
		resp = self.client.get('/%s' % (self.test_jp2_color_id,))
		self.assertEqual(resp.status_code, 303)

	def test_bare_identifier_request_gets_info(self):
		# This is nearly a copy of 
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