# parameter_tests.py
# Tests for Parameter classes.

from patokah import RegionParameter
from patokah import SizeParameter
from patokah import RotationParameter
from patokah import BadRegionSyntaxException
from patokah import BadSizeSyntaxException
from patokah import create_app
from os import path

import unittest

class Tests(unittest.TestCase):
	def __init__(self):
		# TODO: create an instance of the app here that we can use in tests
		self.app = create_app(test=True)
		## with self.app we can do, e.g.:
		# c = Client(self.app, BaseResponse)
		# resp = c.get('/pudl0001/4609321/s42/00000004/NaN,10,70,80/full/0/native.jpg')
		## and then test the response.
		## see http://werkzeug.pocoo.org/docs/test/
		self.test_jp2_id = 'pudl0001/4609321/s42/00000004'
		self.test_jp2_path = os.path.join(os.path.dirname(__file__), 'lib')
		pass

	def setUp(self):
		unittest.TestCase.setUp(self)
		

	def test_resolve_id(self):
		pass

	def test_img_info:
		pass


	def test_region_full(self):
		url_segment = 'full'
		expected_mode = 'full'
		region_parameter = RegionParameter(url_segment)
		self.assertEqual(region_parameter.mode, expected_mode)

	def test_region_pct(self):
		url_segment = 'pct:10,11,70.5,80'

		expected_mode = 'pct'
		expected_x = 10.0
		expected_y = 11.0
		expected_w = 70.5
		expected_h = 80.0

		region_parameter = RegionParameter(url_segment)
		self.assertEqual(region_parameter.mode, expected_mode)
		self.assertEqual(region_parameter.x, expected_x)
		self.assertEqual(region_parameter.y, expected_y)
		self.assertEqual(region_parameter.w, expected_w)
		self.assertEqual(region_parameter.h, expected_h)

	def test_region_pixel(self):
		url_segment = '80,50,16,75'

		expected_mode = 'pixel'
		expected_x = 80
		expected_y = 50
		expected_w = 16
		expected_h = 75

		region_parameter = RegionParameter(url_segment)
		self.assertEqual(region_parameter.mode, expected_mode)
		self.assertEqual(region_parameter.x, expected_x)
		self.assertEqual(region_parameter.y, expected_y)
		self.assertEqual(region_parameter.w, expected_w)
		self.assertEqual(region_parameter.h, expected_h)

	def test_pct_le_100_exception(self):
		url_segment = 'pct:101,70,50,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

		url_segment = 'pct:100,100.1,50,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

	def test_missing_dim_exception(self):
		url_segment = 'pct:101,70,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

		url_segment = '100,50,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

	def test_size_full(self):
		url_segment = 'full'
		expected_mode = 'full'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.mode, expected_mode)

	def test_size_pct(self):
		url_segment = 'pct:50'
		expected_mode = 'pct'
		expected_pct = 50.0
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.pct, expected_pct)

	def test_size_gtlt_100_pct_exception(self):
		url_segment = 'pct:101'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

		url_segment = 'pct:-0.1'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

	def test_size_h_only(self):
		url_segment = ',100'
		expected_mode = 'pixel'
		expected_height = 100
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.w, None)
		self.assertEqual(size_parameter.mode, expected_mode)

	def test_size_w_only(self):
		url_segment = '500,'
		expected_mode = 'pixel'
		expected_width = 500
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, None)
		self.assertEqual(size_parameter.force_aspect, None)
		self.assertEqual(size_parameter.mode, expected_mode)

	def test_size_force_aspect(self):
		url_segment = '500,100'
		expected_mode = 'pixel'
		expected_width = 500
		expected_height = 100
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.force_aspect, True)
		self.assertEqual(size_parameter.mode, expected_mode)

	def test_size_not_force_aspect(self):
		url_segment = '!500,100'
		expected_mode = 'pixel'
		expected_width = 500
		expected_height = 100
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.force_aspect, False)
		self.assertEqual(size_parameter.mode, expected_mode)

	def test_dimension_lt_1_px_exception(self):
		url_segment = '-1,500'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

		url_segment = '500,-1'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

		url_segment = '!500,-1'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

		url_segment = ',-30'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

		url_segment = '-50,'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

	# rotation tests also test the kdu args since we don't need any image info
	def test_rotation_0(self):
		url_segment = '0'
		expected_rotation = 0
		expected_kdu_arg = ''
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_kdu_arg(), expected_kdu_arg)

	def test_rotation_neg_75(self):
		url_segment = '-75'
		expected_rotation = -90
		expected_kdu_arg = '-rotate -90'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_kdu_arg(), expected_kdu_arg)

	def test_rotation_91(self):
		url_segment = '91'
		expected_rotation = 90
		expected_kdu_arg = '-rotate 90'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_kdu_arg(), expected_kdu_arg)

	def test_rotation_314(self):
		url_segment = '314'
		expected_rotation = 270
		expected_kdu_arg = '-rotate 270'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_kdu_arg(), expected_kdu_arg)

	def test_rotation_315(self):
		url_segment = '315'
		expected_rotation = 360
		expected_kdu_arg = ''
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_kdu_arg(), expected_kdu_arg)

if __name__ == "__main__":
	unittest.main()