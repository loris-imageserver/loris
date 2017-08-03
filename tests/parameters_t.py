# parameters_t.py
#-*- coding: utf-8 -*-

from __future__ import absolute_import

from decimal import Decimal

from hypothesis import given
from hypothesis.strategies import text
import pytest

from loris import img_info
from loris.loris_exception import RequestException, SyntaxException
from loris.parameters import (
	FULL_MODE, PCT_MODE, PIXEL_MODE,
	RegionParameter, RotationParameter, SizeParameter,
)
from tests import loris_t

"""
Parameter object tests. To run this test on its own, do:

$ python -m unittest -v tests.parameters_t

from the `/loris` (not `/loris/loris`) directory.
"""

def build_image_info(width=100, height=100):
	"""Produces an ``ImageInfo`` object of the given dimensions."""
	info = img_info.ImageInfo()
	info.width = width
	info.height = height
	return info


class _ParameterTest(loris_t.LorisTest):
	def _get_info_long_y(self):
		# jp2, y is long dimension
		fp = self.test_jp2_color_fp
		fmt = self.test_jp2_color_fmt
		ident = self.test_jp2_color_id
		uri = self.test_jp2_color_uri
		return img_info.ImageInfo.from_image_file(uri, fp, fmt)

	def _get_info_long_x(self):
		# jpeg, x is long dimension
		fp = self.test_jpeg_fp
		fmt = self.test_jpeg_fmt
		ident = self.test_jpeg_id
		uri = self.test_jpeg_uri
		return img_info.ImageInfo.from_image_file(uri, fp, fmt)


class TestRegionParameter(_ParameterTest):
	def test_populate_slots_from_pct(self):
		info = self._get_info_long_y()
		rp = RegionParameter('pct:25,25,50,50', info)
		self.assertEquals(rp.pixel_x, int(info.width*0.25))
		self.assertEquals(rp.pixel_y, int(info.height*0.25))
		self.assertEquals(rp.pixel_w, int(info.width*0.50))
		self.assertEquals(rp.pixel_h, int(info.height*0.50))
		self.assertEquals(rp.decimal_x, Decimal('0.25'))
		self.assertEquals(rp.decimal_y, Decimal('0.25'))
		self.assertEquals(rp.decimal_w, Decimal('0.50'))
		self.assertEquals(rp.decimal_h, Decimal('0.50'))

	def test_populate_slots_from_pixel(self):
		info = self._get_info_long_x()
		rp = RegionParameter('797,900,1594,1600', info)
		self.assertEquals(rp.pixel_x, 797)
		self.assertEquals(rp.pixel_y, 900)
		self.assertEquals(rp.pixel_w, 1594)
		self.assertEquals(rp.pixel_h, 1600)
		self.assertEquals(rp.decimal_x, rp.pixel_x / Decimal(str(info.width)))
		self.assertEquals(rp.decimal_y, rp.pixel_y / Decimal(str(info.height)))
		self.assertEquals(rp.decimal_w, rp.pixel_w / Decimal(str(info.width)))
		self.assertEquals(rp.decimal_h, rp.pixel_h / Decimal(str(info.height)))

	def test_square_mode_long_y(self):
		# 5906 x 7200
		info = self._get_info_long_y()
		rp = RegionParameter('square', info)
		self.assertEquals(rp.pixel_x, 0)
		self.assertEquals(rp.pixel_y, 647)
		self.assertEquals(rp.pixel_w, 5906)
		self.assertEquals(rp.pixel_h, 5906)

	def test_square_mode_long_x(self):
		# 3600 x 2987
		info = self._get_info_long_x()
		rp = RegionParameter('square', info)
		self.assertEquals(rp.pixel_x, 306)
		self.assertEquals(rp.pixel_y, 0)
		self.assertEquals(rp.pixel_w, 2987)
		self.assertEquals(rp.pixel_h, 2987)

	def test_recognise_full_mode_if_correct_dimensions(self):
		info = build_image_info(1500, 800)
		rp = RegionParameter('0,0,1500,800', info)
		self.assertEquals(rp.mode, FULL_MODE)

	def test_anything_except_four_coordinates_is_error(self):
		info = build_image_info()
		with self.assertRaises(SyntaxException):
			RegionParameter('pct:100', info)

	def test_percentage_greater_than_100_is_error(self):
		info = build_image_info()
		with self.assertRaises(RequestException):
			RegionParameter('pct:150,150,150,150', info)

	def test_x_parameter_greater_than_width_is_error(self):
		info = build_image_info(width=100)
		with self.assertRaises(RequestException):
			RegionParameter('200,0,100,100', info)

	def test_y_parameter_greater_than_height_is_error(self):
		info = build_image_info(height=100)
		with self.assertRaises(RequestException):
			RegionParameter('0,200,100,100', info)

	def test_canonical_uri_value_oob_w_pixel(self):
		info = self._get_info_long_x() # x is long dimension
		x = 200
		offset = 1
		oob_w = info.width - x + offset
		rp = RegionParameter('%d,13,%d,17' % (x,oob_w), info)
		expected_canonical = '%d,13,%d,17' % (x, info.width - x)
		# Note that the below will need to be changed if decimal precision is
		# changed (currently 25 places)
		self.assertEquals(rp.decimal_w, Decimal('0.9444444444444444444444444'))
		self.assertEquals(rp.canonical_uri_value, expected_canonical)

	def test_canonical_uri_value_oob_w_pct(self):
		info = self._get_info_long_y() # y is long dimension
		x = 20
		w = 81
		rp = RegionParameter('pct:%d,13,%d,27' % (x,w), info)
		self.assertEquals(rp.decimal_w, Decimal('0.8'))
		expected_canonical = '1181,936,4725,1944'
		self.assertEquals(rp.canonical_uri_value, expected_canonical)

	def test_canonical_uri_value_oob_y_pixel(self):
		info = self._get_info_long_y() # y is long dimension
		y = 300
		offset = 1 # request would be this many pixels OOB
		oob_h = info.height - y + offset
		rp = RegionParameter('29,%d,31,%d' % (y,oob_h), info)
		expected_canonical = '29,%d,31,%d' % (y, info.height - y)
		self.assertEquals(rp.canonical_uri_value, expected_canonical)

	def test_canonical_uri_value_oob_y_pct(self):
		info = self._get_info_long_x() # x is long dimension
		y = 28.3
		h = 72.2
		rp = RegionParameter('pct:13,%f,17,%f' % (y,h), info)
		expected_canonical = '468,845,612,2142'
		self.assertEquals(rp.canonical_uri_value, expected_canonical)

	def test_syntax_exceptions(self):
		info = self._get_info_long_y()
		with self.assertRaises(SyntaxException):
			RegionParameter('n:1,2,3,4', info)
		with self.assertRaises(SyntaxException):
			RegionParameter('1,2,3,q', info)
		with self.assertRaises(SyntaxException):
			RegionParameter('1,2,3', info)
		with self.assertRaises(SyntaxException):
			RegionParameter('something', info)

	def test_request_exceptions(self):
		info = self._get_info_long_y()
		with self.assertRaises(RequestException):
			RegionParameter('1,2,0,3', info)
		with self.assertRaises(RequestException):
			RegionParameter('1,2,3,0', info)
		with self.assertRaises(RequestException):
			RegionParameter('pct:100,2,3,0', info)

	def test_str(self):
		info = self._get_info_long_y()
		rp1 = RegionParameter('full', info)
		self.assertEquals(str(rp1), 'full')

		rp2 = RegionParameter('125,15,120,140', info)
		self.assertEquals(str(rp2), '125,15,120,140')

		rp3 = RegionParameter('pct:41.6,7.5,40,70', info)
		self.assertEquals(str(rp3), 'pct:41.6,7.5,40,70')

		rp4 = RegionParameter('125,15,200,200', info)
		self.assertEquals(str(rp4), '125,15,200,200')

		rp5 = RegionParameter('pct:41.6,7.5,66.6,100', info)
		self.assertEquals(str(rp5), 'pct:41.6,7.5,66.6,100')


class TestSizeParameter(_ParameterTest):
	def test_exceptions(self):
		info = self._get_info_long_y()
		rp = RegionParameter('pct:25,25,75,75', info)
		with self.assertRaises(SyntaxException):
			SizeParameter('!25,', rp)
		with self.assertRaises(SyntaxException):
			SizeParameter('!25', rp)
		with self.assertRaises(SyntaxException):
			SizeParameter('25', rp)

	def test_zero_or_negative_percentage_is_rejected(self):
		info = build_image_info(100, 100)
		rp = RegionParameter('full', info)
		with self.assertRaises(RequestException):
			SizeParameter('pct:0', rp)

	def test_very_small_pixel_width_is_positive(self):
		info = build_image_info(width=1, height=100)
		rp = RegionParameter('full', info)
		sp = SizeParameter(',50', rp)
		self.assertEquals(sp.w, 1)

	def test_very_small_pixel_height_is_positive(self):
		info = build_image_info(width=100, height=1)
		rp = RegionParameter('full', info)
		sp = SizeParameter('50,', rp)
		self.assertEquals(sp.h, 1)

	def test_very_small_percentage_width_is_positive(self):
		info = build_image_info(width=1, height=100)
		rp = RegionParameter('full', info)
		sp = SizeParameter('pct:50', rp)
		self.assertEquals(sp.w, 1)

	def test_negative_x_percentage_is_rejected(self):
		info = build_image_info()
		with self.assertRaises(RequestException):
			rp = RegionParameter('pct:-5,100,100,100', info)

	def test_negative_y_percentage_is_rejected(self):
		info = build_image_info()
		with self.assertRaises(RequestException):
			rp = RegionParameter('pct:100,-5,100,100', info)

	def test_str_representation(self):
		info = build_image_info()
		rp = RegionParameter('full', info)
		for uri_value in [
			'full',
			'pct:50',
			'50,',
			',50',
			'!50,50',
		]:
			sp = SizeParameter(uri_value, rp)
			self.assertEquals(str(sp), uri_value)

	def test_very_small_percentage_height_is_positive(self):
		info = build_image_info(width=100, height=1)
		rp = RegionParameter('full', info)
		sp = SizeParameter('pct:50', rp)
		self.assertEquals(sp.h, 1)

	def test_populate_slots_from_full(self):
		# full
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter('full',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, FULL_MODE)
		self.assertEquals(sp.canonical_uri_value, FULL_MODE)

		rp = RegionParameter('256,256,256,256', info)
		sp = SizeParameter('full',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, FULL_MODE)
		self.assertEquals(sp.canonical_uri_value, FULL_MODE)

	def test_populate_slots_from_pct(self):
		# pct:n
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.canonical_uri_value, '1476,')

		rp = RegionParameter('256,256,256,256', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.canonical_uri_value, '64,')

		rp = RegionParameter('pct:0,0,50,50', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.canonical_uri_value, '738,')

	def test_populate_slots_from_w_only(self):
		# w,
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter('180,',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '180,')

		rp = RegionParameter('200,300,500,600', info)
		sp = SizeParameter('125,',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '125,')
                self.assertEquals(type(sp.w), int)
                self.assertEquals(sp.w, 125)
                self.assertEquals(type(sp.h), int)
                self.assertEquals(sp.h, 150)

        def test_tiny_image(self):
		info = self._get_info_long_x()
		rp = RegionParameter('full', info)
		sp = SizeParameter('1,', rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '1,')
                self.assertEquals(sp.w, 1)
                self.assertEquals(sp.h, 1)

	def test_populate_slots_from_h_only(self):
		# ,h
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter(',90',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '73,')

		rp = RegionParameter('50,290,360,910', info)
		sp = SizeParameter(',275',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '108,')

	def test_populate_slots_from_wh(self):
		# w,h
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter('48,48',rp)
		self.assertEquals(sp.force_aspect, True)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '48,48')

		rp = RegionParameter('15,16,23,42', info)
		sp = SizeParameter('60,60',rp) # upsample!
		self.assertEquals(sp.force_aspect, True)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '60,60')

	def test_populate_slots_from_bang_wh(self):
		# !w,h
		info = self._get_info_long_y()

		rp = RegionParameter('full', info)
		sp = SizeParameter('!120,140',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '114,')

		rp = RegionParameter('0,0,125,160', info)
		sp = SizeParameter('!120,140',rp,)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '109,')

		rp = RegionParameter('0,0,125,160', info)
		sp = SizeParameter('!130,140',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '109,')

		rp = RegionParameter('50,80,140,160', info)
		sp = SizeParameter('!130,180',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '130,')

		rp = RegionParameter('50,80,140,160', info)
		sp = SizeParameter('!145,165',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '144,')

		rp = RegionParameter('50,80,140,180', info)
		sp = SizeParameter('!145,185',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.canonical_uri_value, '143,')

	def test_zero_width_or_height_is_rejected(self):
		info = build_image_info()
		rp = RegionParameter('full', info)
		with pytest.raises(RequestException):
			SizeParameter('0,', rp)
		with pytest.raises(RequestException):
			SizeParameter(',0', rp)
		with pytest.raises(RequestException):
			SizeParameter('0,0', rp)

	@given(text(alphabet='0123456789.,!'))
	def test_parsing_parameter_either_passes_or_is_exception(self, uri_value):
		info = build_image_info()
		rp = RegionParameter('full', info)
		try:
			SizeParameter(uri_value, rp)
		except (RequestException, SyntaxException):
			pass


class TestRotationParameter(_ParameterTest):
	def test_exceptions(self):
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('a')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('361')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('-1')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('!-1')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('!361')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('-0.1')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('1.3.6')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('!2.7.13')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('.')
		with self.assertRaises(SyntaxException):
			rp = RotationParameter('.0.')

	@given(text(alphabet='0123456789.!'))
	def test_parsing_parameter_either_passes_or_is_syntaxexception(self, xs):
	    try:
	        RotationParameter(xs)
	    except SyntaxException:
	        pass

	def test_uri_value(self):
		rp = RotationParameter('0')
		self.assertEquals(rp.rotation, '0')

		rp = RotationParameter('46')
		self.assertEquals(rp.rotation, '46')

		rp = RotationParameter('180')
		self.assertEquals(rp.rotation, '180')

	def test_mirroring(self):
		rp = RotationParameter('180')
		self.assertFalse(rp.mirror)

		rp = RotationParameter('!180')
		self.assertTrue(rp.mirror)

	def test_c14n(self):
		rp = RotationParameter('42.10')
		self.assertEquals(rp.canonical_uri_value, '42.1')

		rp = RotationParameter('180.0')
		self.assertEquals(rp.canonical_uri_value, '180')

		rp = RotationParameter('!180.0')
		self.assertEquals(rp.canonical_uri_value, '!180')

		rp = RotationParameter('!180.10')
		self.assertEquals(rp.canonical_uri_value, '!180.1')


def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(TestRegionParameter, 'test'))
	test_suites.append(unittest.makeSuite(TestSizeParameter, 'test'))
	test_suites.append(unittest.makeSuite(TestRotationParameter, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite
