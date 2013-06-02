# img_info_t.py
#-*- coding: utf-8 -*-

from loris import img_info
from os import path
import json
import loris_t

"""
Info unit and function tests. To run this test on its own, do:

$ python -m unittest -v tests.img_info_t

from the `/loris` (not `/loris/loris`) directory.
"""

class B_InfoUnitTests(loris_t.LorisTest):
	'Tests ImageInfo constructors.'
	def test_color_jp2_info_from_image(self):
		fp = self.test_jp2_color_fp
		fmt = self.test_jp2_color_fmt
		ident = self.test_jp2_color_id
		uri = self.test_jp2_color_uri

		info = img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

		self.assertEqual(info.width, self.test_jp2_color_dims[0])
		self.assertEqual(info.height, self.test_jp2_color_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey','color'])
		self.assertEqual(info.tile_width, self.test_jp2_color_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_color_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16])
		self.assertEqual(info.ident, uri)

	def test_grey_jp2_info_from_image(self):
		fp = self.test_jp2_grey_fp
		fmt = self.test_jp2_grey_fmt
		ident = self.test_jp2_grey_id
		uri = self.test_jp2_grey_uri

		info = img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

		self.assertEqual(info.width, self.test_jp2_grey_dims[0])
		self.assertEqual(info.height, self.test_jp2_grey_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey'])
		self.assertEqual(info.tile_width, self.test_jp2_grey_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_grey_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16,32])
		self.assertEqual(info.ident, uri)

	def test_jpeg_info_from_image(self):
		fp = self.test_jpeg_fp
		fmt = self.test_jpeg_fmt
		ident = self.test_jpeg_id
		uri = self.test_jpeg_uri

		info = img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

		self.assertEqual(info.width, self.test_jpeg_dims[0])
		self.assertEqual(info.height, self.test_jpeg_dims[1])
		self.assertEqual(info.qualities, ['native','color','grey','bitonal'])
		self.assertEqual(info.scale_factors, None)
		self.assertEqual(info.ident, uri)

	def test_tiff_info_from_image(self):
		fp = self.test_tiff_fp
		fmt = self.test_tiff_fmt
		ident = self.test_tiff_id
		uri = self.test_tiff_uri

		info = img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

		self.assertEqual(info.width, self.test_tiff_dims[0])
		self.assertEqual(info.height, self.test_tiff_dims[1])
		self.assertEqual(info.qualities, ['native','color','grey','bitonal'])
		self.assertEqual(info.scale_factors, None)
		self.assertEqual(info.ident, uri)

	def test_info_from_json(self):
		json_fp = self.test_jp2_color_info_fp
		
		info = img_info.ImageInfo.from_json(json_fp)

		self.assertEqual(info.width, self.test_jp2_color_dims[0])
		self.assertEqual(info.height, self.test_jp2_color_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey','color'])
		self.assertEqual(info.tile_width, self.test_jp2_color_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_color_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16])
		self.assertEqual(info.ident, self.test_jp2_color_uri)


class C_InfoFunctionalTests(loris_t.LorisTest):
	'Simulate working with the API over HTTP.'

	def test_jp2_info_dot_json_request(self):
		resp = self.client.get('/%s/%s' % (self.test_jp2_color_id,'info.json'))
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
		self.assertEqual(info.ident, self.test_jp2_color_uri)

	# def test_jp2_info_json_request(self):
	# 	'test conneg'
	# 	resp = self.client.get('/%s/%s' % (self.test_jp2_color_id,'info'))


class D_InfoCacheTests(loris_t.LorisTest):
	pass
#
# 	def test_info_cache(self):
# 		pass

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(B_InfoUnitTests, 'test'))
	test_suites.append(unittest.makeSuite(C_InfoFunctionalTests, 'test'))
	test_suites.append(unittest.makeSuite(D_InfoCacheTests, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite