# parameters_t.py
#-*- coding: utf-8 -*-

from decimal import Decimal
from loris import img_info
from loris.parameters import BadRegionRequestException
from loris.parameters import BadRegionSyntaxException
from loris.parameters import RegionParameter
import loris_t

"""
Parameter object tests. To run this test on its own, do:

$ python -m unittest -v tests.parameters_t

from the `/loris` (not `/loris/loris`) directory.
"""

# TODO: bring over old tile-generator test for precision checking.

class G_RegionParameterUnitTests(loris_t.LorisTest):

	def __get_info(self):
		# jp2, y is long dimension
		fp = self.test_jp2_color_fp
		fmt = self.test_jp2_color_fmt
		ident = self.test_jp2_color_id
		uri = self.test_jp2_color_uri
		return img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

	def __get_info2(self):
		# jpeg, x is long dimension
		fp = self.test_jpeg_fp
		fmt = self.test_jpeg_fmt
		ident = self.test_jpeg_id
		uri = self.test_jpeg_uri
		return img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

	def test_a_populate_slots_from_pct(self):
		info = self.__get_info()
		rp = RegionParameter('pct:25,25,50,50', info)
		self.assertEquals(rp.pixel_x, int(info.width*0.25))
		self.assertEquals(rp.pixel_y, int(info.height*0.25))
		self.assertEquals(rp.pixel_w, int(info.width*0.50))
		self.assertEquals(rp.pixel_h, int(info.height*0.50))
		self.assertEquals(rp.decimal_x, Decimal(0.25))
		self.assertEquals(rp.decimal_y, Decimal(0.25))
		self.assertEquals(rp.decimal_w, Decimal(0.50))
		self.assertEquals(rp.decimal_h, Decimal(0.50))

	def test_b_populate_slots_from_pixel(self):
		info = self.__get_info2()
		rp = RegionParameter('797,900,1594,1600', info)
		self.assertEquals(rp.pixel_x, 797) 
		self.assertEquals(rp.pixel_y, 900) 
		self.assertEquals(rp.pixel_w, 1594)
		self.assertEquals(rp.pixel_h, 1600)
		self.assertEquals(rp.decimal_x, rp.pixel_x / Decimal(info.width))
		self.assertEquals(rp.decimal_y, rp.pixel_y / Decimal(info.height))
		self.assertEquals(rp.decimal_w, rp.pixel_w / Decimal(info.width))
		self.assertEquals(rp.decimal_h, rp.pixel_h / Decimal(info.height))

	def test_c_cannonical_uri_value_oob_w_pixel(self):
		info = self.__get_info2()
		x = 200
		offset = 1
		oob_w = info.width - x + offset
		rp = RegionParameter('%d,13,%d,17' % (x,oob_w), info)
		expected_cannonical = '%d,13,%d,17' % (x, info.width - x)
		# Note that the below will need to be changed if decimal precision is
		# changed (currently 25 places)
		self.assertEquals(rp.decimal_w, Decimal('0.9444444444444444444444444'))
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)

	def test_d_cannonical_uri_value_oob_w_pct(self):
		info = self.__get_info()
		x = 20
		w = 81
		rp = RegionParameter('pct:%d,13,%d,27' % (x,w), info)
		self.assertEquals(rp.decimal_w, Decimal('0.8'))
		expected_cannonical = '638,468,2550,972'
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)

	def test_e_cannonical_uri_value_oob_y_pixel(self):
		info = self.__get_info()
		y = 300
		offset = 1
		oob_h = info.height - y + offset
		rp = RegionParameter('29,%d,31,%d' % (y,oob_h), info)
		expected_cannonical = '29,%d,31,%d' % (y, info.height - y)
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)

	def test_f_cannonical_uri_value_oob_y_pct(self):
		info = self.__get_info2()
		y = 28.3
		h = 72.2
		rp = RegionParameter('pct:13,%f,17,%f' % (y,h), info)
		expected_cannonical = '468,845,612,2142'
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)		

	def test_g_exceptions(self):
		info = self.__get_info()
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter('n:1,2,3,4', info)
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter('1,2,3,q', info)
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter('1,2,3', info)
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter('something', info)
		with self.assertRaises(BadRegionRequestException):
			RegionParameter('1,2,0,3', info)
		with self.assertRaises(BadRegionRequestException):
			RegionParameter('1,2,3,0', info)
		with self.assertRaises(BadRegionRequestException):
			RegionParameter('pct:100,2,3,0', info)

class H_RegionParameterFunctionalTests(loris_t.LorisTest):
	# TODO: with client once other parameters are impl.
	pass

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(G_RegionParameterUnitTests, 'test'))
	test_suites.append(unittest.makeSuite(H_RegionParameterFunctionalTests, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite