# img_info_t.py
#-*- coding: utf-8 -*-

import loris_t
from loris import img_info

"""
Info tests. This may need to be modified if you change the resolver 
implementation. To run this test on its own, do:

$ python -m unittest tests.img_info_t

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