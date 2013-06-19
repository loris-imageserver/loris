# parameters_t.py
#-*- coding: utf-8 -*-

from decimal import Decimal
from loris import img_info
from loris.parameters import DECIMAL_ONE
from loris.parameters import FULL_MODE
from loris.parameters import PCT_MODE
from loris.parameters import PIXEL_MODE
from loris.parameters import RegionParameter
from loris.parameters import RegionRequestException
from loris.parameters import RegionSyntaxException
from loris.parameters import RotationParameter
from loris.parameters import RotationSyntaxException
from loris.parameters import SizeParameter
from loris.parameters import SizeRequestException
from loris.parameters import SizeSyntaxException
import loris_t

"""
Parameter object tests. To run this test on its own, do:

$ python -m unittest -v tests.parameters_t

from the `/loris` (not `/loris/loris`) directory.
"""

# TODO: bring over old tile-generator test for precision checking.
class _ParameterUnitTest(loris_t.LorisTest):
	def _get_info(self):
		# jp2, y is long dimension
		fp = self.test_jp2_color_fp
		fmt = self.test_jp2_color_fmt
		ident = self.test_jp2_color_id
		uri = self.test_jp2_color_uri
		return img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)

	def _get_info2(self):
		# jpeg, x is long dimension
		fp = self.test_jpeg_fp
		fmt = self.test_jpeg_fmt
		ident = self.test_jpeg_id
		uri = self.test_jpeg_uri
		return img_info.ImageInfo.from_image_file(ident, uri, fp, fmt)


class Test_G_RegionParameterUnit(_ParameterUnitTest):
	def test_a_populate_slots_from_pct(self):
		info = self._get_info()
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
		info = self._get_info2()
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
		info = self._get_info2()
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
		info = self._get_info()
		x = 20
		w = 81
		rp = RegionParameter('pct:%d,13,%d,27' % (x,w), info)
		self.assertEquals(rp.decimal_w, Decimal('0.8'))
		expected_cannonical = '638,468,2550,972'
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)

	def test_e_cannonical_uri_value_oob_y_pixel(self):
		info = self._get_info()
		y = 300
		offset = 1
		oob_h = info.height - y + offset
		rp = RegionParameter('29,%d,31,%d' % (y,oob_h), info)
		expected_cannonical = '29,%d,31,%d' % (y, info.height - y)
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)

	def test_f_cannonical_uri_value_oob_y_pct(self):
		info = self._get_info2()
		y = 28.3
		h = 72.2
		rp = RegionParameter('pct:13,%f,17,%f' % (y,h), info)
		expected_cannonical = '468,845,612,2142'
		self.assertEquals(rp.cannonical_uri_value, expected_cannonical)		

	def test_g_exceptions(self):
		info = self._get_info()
		with self.assertRaises(RegionSyntaxException):
			RegionParameter('n:1,2,3,4', info)
		with self.assertRaises(RegionSyntaxException):
			RegionParameter('1,2,3,q', info)
		with self.assertRaises(RegionSyntaxException):
			RegionParameter('1,2,3', info)
		with self.assertRaises(RegionSyntaxException):
			RegionParameter('something', info)
		with self.assertRaises(RegionRequestException):
			RegionParameter('1,2,0,3', info)
		with self.assertRaises(RegionRequestException):
			RegionParameter('1,2,3,0', info)
		with self.assertRaises(RegionRequestException):
			RegionParameter('pct:100,2,3,0', info)

class Test_H_RegionParameterFunctional(_ParameterUnitTest):
	# TODO: with client once other parameters are impl.
	pass

class Test_I_SizeParameterUnit(_ParameterUnitTest):
	def test_a_exceptions(self):
		info = self._get_info()
		rp = RegionParameter('pct:25,25,75,75', info)
		with self.assertRaises(SizeSyntaxException):
			SizeParameter('!25,',rp)
		with self.assertRaises(SizeSyntaxException):
			SizeParameter('!25',rp)
		with self.assertRaises(SizeSyntaxException):
			SizeParameter('25',rp)

	def test_b_populate_slots_from_full(self):
		# full
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter('full',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, FULL_MODE)
		self.assertEquals(sp.cannonical_uri_value, FULL_MODE)

		rp = RegionParameter('256,256,256,256', info)
		sp = SizeParameter('full',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, FULL_MODE)
		self.assertEquals(sp.cannonical_uri_value, FULL_MODE)

	def test_c_populate_slots_from_pct(self):
		# pct:n
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.cannonical_uri_value, '797,900')

		rp = RegionParameter('256,256,256,256', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.cannonical_uri_value, '64,64')

		rp = RegionParameter('pct:0,0,50,50', info)
		sp = SizeParameter('pct:25',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PCT_MODE)
		self.assertEquals(sp.cannonical_uri_value, '398,450')

	def test_c_populate_slots_from_w_only(self):
		# w,
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter('180,',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '180,203')

		rp = RegionParameter('200,300,500,600', info)
		sp = SizeParameter('125,',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '125,150')

	def test_d_populate_slots_from_h_only(self):
		# ,h
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter(',90',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '79,90')

		rp = RegionParameter('50,290,360,910', info)
		sp = SizeParameter(',275',rp)
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '108,275')

	def test_e_populate_slots_from_wh(self):
		# w,h
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter('48,48',rp)
		self.assertEquals(sp.force_aspect, True)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '48,48')

		rp = RegionParameter('15,16,23,42', info)
		sp = SizeParameter('60,60',rp) # upsample!
		self.assertEquals(sp.force_aspect, True)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '60,60')

	def test_f_populate_slots_from_bang_wh(self):
		# !w,h
		info = self._get_info()

		rp = RegionParameter('full', info)
		sp = SizeParameter('!120,140',rp, 'w') # preserve width
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '120,135')
		
		rp = RegionParameter('full', info)
		sp = SizeParameter('!120,140',rp, 'h') # preserve height
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '123,140')

		rp = RegionParameter('0,0,125,160', info)
		sp = SizeParameter('!120,140',rp,'w') # preserve width
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '120,153')

		rp = RegionParameter('0,0,125,160', info)
		sp = SizeParameter('!120,140',rp,'h') # preserve height
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '109,140')

		# OOB w, preferring w, with in bounds h
		rp = RegionParameter('0,0,125,160', info)
		sp = SizeParameter('!130,140',rp,'w') # try to preserve width
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '109,140') # but height is preserved

		# OOB h, preferring h, with in bounds w.
		rp = RegionParameter('50,80,140,160', info)
		sp = SizeParameter('!130,180',rp,'h') # try to preserve height
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '130,148') # but width is preserved

		# all OOB, should act like anyt other req.
		rp = RegionParameter('50,80,140,160', info)
		sp = SizeParameter('!145,165',rp,'h') # prefer h
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '144,165')

		rp = RegionParameter('50,80,140,180', info)
		sp = SizeParameter('!145,185',rp,'w') # prefer w
		self.assertEquals(sp.force_aspect, False)
		self.assertEquals(sp.mode, PIXEL_MODE)
		self.assertEquals(sp.cannonical_uri_value, '145,186')

class Test_J_SizeParameterFunctional(_ParameterUnitTest):
	# TODO: with client once other parameters are impl.
	pass

class Test_K_RotationParameterUnit(_ParameterUnitTest):
	def test_a_exceptions(self):
		with self.assertRaises(RotationSyntaxException):
			rp = RotationParameter('a')
		with self.assertRaises(RotationSyntaxException):
			rp = RotationParameter('361')
		with self.assertRaises(RotationSyntaxException):
			rp = RotationParameter('-1')

	def test_b_rounding(self):
		rp = RotationParameter('44')
		self.assertEquals(rp.cannonical_uri_value, '44')

		rp = RotationParameter('46')
		self.assertEquals(rp.cannonical_uri_value, '46')

		rp = RotationParameter('269')
		self.assertEquals(rp.cannonical_uri_value, '269')

		rp = RotationParameter('316')
		self.assertEquals(rp.cannonical_uri_value, '316')

class Test_L_RotationParameterFunctional(_ParameterUnitTest):
	# TODO: with client once other parameters are impl.
	pass

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(Test_G_RegionParameterUnit, 'test'))
	test_suites.append(unittest.makeSuite(Test_H_RegionParameterFunctional, 'test'))
	test_suites.append(unittest.makeSuite(Test_I_SizeParameterUnit, 'test'))
	test_suites.append(unittest.makeSuite(Test_J_SizeParameterFunctional, 'test'))
	test_suites.append(unittest.makeSuite(Test_K_RotationParameterUnit, 'test'))
	test_suites.append(unittest.makeSuite(Test_L_RotationParameterFunctional, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite