# img_info_t.py
#-*- coding: utf-8 -*-

from loris import img_info
import json
import loris_t

"""
Info unit and function tests. To run this test on its own, do:

$ python -m unittest -v tests.img_info_t

from the `/loris` (not `/loris/loris`) directory.
"""

class B_InfoUnitTests(loris_t.LorisTest):
	'Test that the ID resolver works'

	def test_color_jp2_info_from_image(self):
		fp = self.test_jp2_color_fp
		fmt = self.test_jp2_color_fmt
		ident = self.test_jp2_color_id
		info = img_info.ImageInfo.from_image_file(ident, fp, fmt)
		self.assertEqual(info.width, self.test_jp2_color_dims[0])
		self.assertEqual(info.height, self.test_jp2_color_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey','color'])
		self.assertEqual(info.tile_width, self.test_jp2_color_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_color_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16])

	def test_grey_jp2_info_from_image(self):
		fp = self.test_jp2_grey_fp
		fmt = self.test_jp2_grey_fmt
		ident = self.test_jp2_grey_id

		info = img_info.ImageInfo.from_image_file(ident, fp, fmt)
		self.assertEqual(info.width, self.test_jp2_grey_dims[0])
		self.assertEqual(info.height, self.test_jp2_grey_dims[1])
		self.assertEqual(info.qualities, ['native','bitonal','grey'])
		self.assertEqual(info.tile_width, self.test_jp2_grey_tile_dims[0])
		self.assertEqual(info.tile_height, self.test_jp2_grey_tile_dims[1])
		self.assertEqual(info.scale_factors, [1,2,4,8,16,32])

	def test_jpeg_info_from_image(self):
		fp = self.test_jpeg_fp
		fmt = self.test_jpeg_fmt
		ident = self.test_jpeg_id
		info = img_info.ImageInfo.from_image_file(ident, fp, fmt)
		self.assertEqual(info.width, self.test_jpeg_dims[0])
		self.assertEqual(info.height, self.test_jpeg_dims[1])
		self.assertEqual(info.qualities, ['native','color','grey','bitonal'])
		self.assertEqual(info.scale_factors, None)

	def test_tiff_info_from_image(self):
		fp = self.test_tiff_fp
		fmt = self.test_tiff_fmt
		ident = self.test_tiff_id
		info = img_info.ImageInfo.from_image_file(ident, fp, fmt)
		self.assertEqual(info.width, self.test_tiff_dims[0])
		self.assertEqual(info.height, self.test_tiff_dims[1])
		self.assertEqual(info.qualities, ['native','color','grey','bitonal'])
		self.assertEqual(info.scale_factors, None)

	def test_info_from_json(self):
		info_json = '''\
		'''


class C_InfoFunctionalTests(loris_t.LorisTest):
	'Test that the ID resolver works'

	def test_jp2_request(self):
		pass

class D_InfoCacheTests(loris_t.LorisTest):
	'Test that the ID resolver works'

	def test_info_cache(self):
		pass

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(B_InfoUnitTests, 'test'))
	test_suites.append(unittest.makeSuite(C_InfoFunctionalTests, 'test'))
	test_suites.append(unittest.makeSuite(D_InfoCacheTests, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite