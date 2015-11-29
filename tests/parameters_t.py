# parameters_t.py
#-*- coding: utf-8 -*-

from decimal import Decimal
from loris import img_info
from loris.loris_exception import RequestException
from loris.loris_exception import SyntaxException
from loris.parameters import DECIMAL_ONE
from loris.parameters import FULL_MODE
from loris.parameters import PCT_MODE
from loris.parameters import PIXEL_MODE
from loris.parameters import RegionParameter
from loris.parameters import RotationParameter
from loris.parameters import SizeParameter
import loris_t

"""
Parameter object tests. To run this test on its own, do:

$ python -m unittest -v tests.parameters_t

from the `/loris` (not `/loris/loris`) directory.
"""

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
		try:
			with self.assertRaises(SyntaxException):
				RegionParameter('n:1,2,3,4', info)
			with self.assertRaises(SyntaxException):
				RegionParameter('1,2,3,q', info)
			with self.assertRaises(SyntaxException):
				RegionParameter('1,2,3', info)
			with self.assertRaises(SyntaxException):
				RegionParameter('something', info)
		except TypeError: # python < 2.7
			self.assertRaises(SyntaxException, RegionParameter, 'something', info)
			self.assertRaises(SyntaxException, RegionParameter, '1,2,3,q', info)
			self.assertRaises(SyntaxException, RegionParameter, '1,2,3', info)
			self.assertRaises(SyntaxException, RegionParameter, 'something', info)

	def test_request_exceptions(self):
		info = self._get_info_long_y()
		try:
			with self.assertRaises(RequestException):
				RegionParameter('1,2,0,3', info)
			with self.assertRaises(RequestException):
				RegionParameter('1,2,3,0', info)
			with self.assertRaises(RequestException):
				RegionParameter('pct:100,2,3,0', info)
		except TypeError: # python < 2.7
			self.assertRaises(RequestException, RegionParameter, '1,2,0,3', info)
			self.assertRaises(RequestException, RegionParameter, '1,2,3,0', info)
			self.assertRaises(RequestException, RegionParameter, 'pct:100,2,3,0', info)


class TestSizeParameter(_ParameterTest):
	def test_exceptions(self):
		info = self._get_info_long_y()
		rp = RegionParameter('pct:25,25,75,75', info)
		try:
			with self.assertRaises(SyntaxException):
				SizeParameter('!25,',rp)
			with self.assertRaises(SyntaxException):
				SizeParameter('!25',rp)
			with self.assertRaises(SyntaxException):
				SizeParameter('25',rp)
		except TypeError: # python < 2.7
			self.assertRaises(SyntaxException, SizeParameter, '!25,', rp)
			self.assertRaises(SyntaxException, SizeParameter, '!25', rp)
			self.assertRaises(SyntaxException, SizeParameter, '25', rp)

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

class TestRotationParameter(_ParameterTest):
	def test_exceptions(self):
		try:
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
		except TypeError: # Python < 2.7
			self.assertRaises(SyntaxException, RotationParameter, 'a')
			self.assertRaises(SyntaxException, RotationParameter, '361')
			self.assertRaises(SyntaxException, RotationParameter, '-1')
			self.assertRaises(SyntaxException, RotationParameter, '!-1')
			self.assertRaises(SyntaxException, RotationParameter, '!361')
			self.assertRaises(SyntaxException, RotationParameter, '-0.1')

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
