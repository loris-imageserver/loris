#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`tests` -- Unit Tests for Loris WSGI JPEG 2000 Server
==========================================================
.. module:: test
   :platform: Unix
   :synopsis: Unit tests are named so that they run in a logical order, which 
   means running e.g. `python -m unittest -vf tests` should make it clearer 
   where the actual failure happened, rather than having to trace back through
   a cascade of failures to find the original fault.

.. moduleauthor:: Jon Stroop <jstroop@princeton.edu>

"""
from datetime import datetime, timedelta
from decimal import getcontext
from json import loads
from loris import BadRegionRequestException
from loris import BadRegionSyntaxException
from loris import BadSizeSyntaxException
from deepzoom import DeepZoomImageDescriptor
from loris import ImgInfo
from loris import RegionParameter
from loris import RotationParameter
from loris import SizeParameter
from loris import create_app
from os import listdir, path, remove
from shutil import rmtree
from sys import stderr, stdout
from werkzeug.datastructures import Headers
from werkzeug.http import http_date, parse_date
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse, Request
from xml.dom.minidom import parseString
from resolver import resolve
import struct
import subprocess
import unittest

# helpers

class LorisTest(unittest.TestCase):
	def setUp(self):
		unittest.TestCase.setUp(self)
		# create an instance of the app here that we can use in tests
		# see http://werkzeug.pocoo.org/docs/test/
		self.app = create_app(test=True)
		getcontext().prec = self.app.decimal_precision
		self.client = Client(self.app, BaseResponse)
		abs_path = path.abspath(path.dirname(__file__))
		self.test_img_dir = path.join(abs_path, 'test_img')
		self.test_jp2_id = 'pudl0001/4609321/s42/00000004' # color; 2717 x 3600
		self.test_jp2_1_id = 'pudl0033/2008/0132/00000001' # color; 5283 x 7200
		self.test_jp2_2_id = 'AC044/c0002/00000043' # grey; 2477 x 3200

	def tearDown(self):
		# empty the cache
		for d in listdir(self.app.cache_root):
			rmtree(path.join(self.app.cache_root, d))
		rmtree(self.app.cache_root)

	def get_jpeg_dimensions(self, path):
		"""Get the dimensions of a JPEG
		"""
		jpeg = open(path, 'r')
		jpeg.read(2)
		b = jpeg.read(1)
		try:
			while (b and ord(b) != 0xDA):
				while (ord(b) != 0xFF): b = jpeg.read(1)
				while (ord(b) == 0xFF): b = jpeg.read(1)
			   
				if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
					jpeg.read(3)
					h, w = struct.unpack(">HH", jpeg.read(4))
					break
				else:
					jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0]) - 2)
				   
				b = jpeg.read(1)
			width = int(w)
			height = int(h)
		except Exception, e:
			raise
		finally:
			jpeg.close()
		return (width, height)

	def _dims_from_uri(self, uri):
		"""Make a request, save it out, and return the dimensions.
		"""
		resp = self.client.get(uri)
		f_name = path.join(self.app.tmp_dir, 'result.jpg')
		f = open(f_name, 'w')
		f.write(resp.data)
		f.close()
		return self.get_jpeg_dimensions(f_name)


class Test_A_ResolveId(LorisTest):
	"""Test that the ID resolver works.
	"""

	def test_loris_resolve_id(self):
		expected_path = path.join(self.test_img_dir, self.test_jp2_id  + '.jp2')
		resolved_path = resolve(self.test_jp2_id)
		self.assertEqual(expected_path, resolved_path)
		self.assertTrue(path.isfile(resolved_path))

class Test_B_InfoExtraction(LorisTest):
	"""Here we extract info from JPEG 2000 files and test against known values.
	"""
	
	def test_img_info(self):
		img = resolve(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)

		self.assertEqual(info.width, 2717)
		self.assertEqual(info.height, 3600)
		self.assertEqual(info.tile_width, 256)
		self.assertEqual(info.tile_height, 256)
		self.assertEqual(info.levels, 5)
		self.assertEqual(info.qualities, ['native', 'bitonal', 'grey', 'color'])
		self.assertEqual(info.id, self.test_jp2_id)
	
	def test_img_info_1(self):
		img = self.app._resolve_identifier(self.test_jp2_1_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_1_id)

		self.assertEqual(info.width, 5283)
		self.assertEqual(info.height, 7200)
		self.assertEqual(info.tile_width, 256)
		self.assertEqual(info.tile_height, 256)
		self.assertEqual(info.levels, 7)
		self.assertEqual(info.qualities, ['native', 'bitonal', 'grey', 'color'])
		self.assertEqual(info.id, self.test_jp2_1_id)

	def test_img_info_2(self):
		img = self.app._resolve_identifier(self.test_jp2_2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_2_id)

		self.assertEqual(info.width, 2477)
		self.assertEqual(info.height, 3200)
		self.assertEqual(info.tile_width, 256)
		self.assertEqual(info.tile_height, 256)
		self.assertEqual(info.levels, 6)
		self.assertEqual(info.qualities, ['native', 'bitonal', 'grey'])
		self.assertEqual(info.id, self.test_jp2_2_id)

	def test_info_json(self):
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info.json')
		resp_json = loads(resp.data)
		self.assertTrue(resp_json.has_key(u'identifier'))
		self.assertEqual(resp_json.get(u'identifier'), u'pudl0001/4609321/s42/00000004')
		self.assertTrue(resp_json.has_key(u'width'))
		self.assertEqual(resp_json.get(u'width'), 2717)
		self.assertTrue(resp_json.has_key(u'height'))
		self.assertEqual(resp_json.get(u'height'), 3600)
		self.assertTrue(resp_json.has_key(u'scale_factors'))
		self.assertEqual(resp_json.get(u'scale_factors'), [1,2,3,4,5])
		self.assertTrue(resp_json.has_key(u'tile_width'))
		self.assertEqual(resp_json.get(u'tile_width'), 256)
		self.assertTrue(resp_json.has_key(u'tile_height'))
		self.assertEqual(resp_json.get(u'tile_height'), 256)
		self.assertTrue(resp_json.has_key(u'formats'))
		self.assertEqual(resp_json.get(u'formats'), [u'jpg', u'png'])
		self.assertTrue(resp_json.has_key(u'qualities'))
		self.assertEqual(resp_json.get(u'qualities'), [u'native', u'bitonal', u'grey', u'color'])
		self.assertTrue(resp_json.has_key(u'profile'))
		self.assertEqual(resp_json.get(u'profile'), u'http://library.stanford.edu/iiif/image-api/compliance.html#level1')

	def test_info_xml(self):
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info.xml')	
		#This is parsable
		dom = parseString(resp.data)
		# info is the root
		self.assertEqual(dom.documentElement.tagName, 'info')

		# TODO: finish. Right now values are tested with the object and json, 
		# but not here

class Test_C_RegionParameter(LorisTest):
	"""Here we construct RegionParameter objects from would-be URI slices and
	test their attributes and methods.
	"""
	def test_full(self):
		url_segment = 'full'
		expected_mode = 'full'
		region_parameter = RegionParameter(url_segment)
		self.assertEqual(region_parameter.mode, expected_mode)

	def test_pct(self):
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

	def test_pixel(self):
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

	def test_missing_dim(self):
		url_segment = 'pct:101,70,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

		url_segment = '100,50,50'
		with self.assertRaises(BadRegionSyntaxException):
			RegionParameter(url_segment)

	def test_xpixel_oob(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = '2717,0,1,1'
		region_parameter = RegionParameter(url_segment)
		with self.assertRaises(BadRegionRequestException):
			region_arg = region_parameter.to_kdu_arg(info)

	def test_ypixel_oob(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = '0,3600,1,1'
		region_parameter = RegionParameter(url_segment)
		with self.assertRaises(BadRegionRequestException):
			region_arg = region_parameter.to_kdu_arg(info)


	def test_pixel_to_kdu_hw(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = '0,0,1358,1800'
		region_parameter = RegionParameter(url_segment)
		expected_kdu = '-region \{0,0\},\{0.5,0.49981597350018402650\}'
		region_arg = region_parameter.to_kdu_arg(info)
		self.assertEqual(region_arg, expected_kdu)

	def test_pixel_to_kdu_tl(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = '1358,1800,200,658'
		region_parameter = RegionParameter(url_segment)
		expected_kdu = '-region \{0.5,0.49981597350018402650\},\{0.18277777777777777778,0.073610599926389400074\}'
		region_arg = region_parameter.to_kdu_arg(info)
		self.assertEqual(region_arg, expected_kdu)

	def test_pct_to_kdu_hw(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = 'pct:0,0,50,50'
		region_parameter = RegionParameter(url_segment)
		expected_kdu = '-region \{0,0\},\{0.5,0.5\}'
		region_arg = region_parameter.to_kdu_arg(info)
		self.assertEqual(region_arg, expected_kdu)

	def test_pct_to_kdu_tl(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = 'pct:50,50,50,50'
		region_parameter = RegionParameter(url_segment)
		expected_kdu = '-region \{0.5,0.5\},\{0.5,0.5\}'
		region_arg = region_parameter.to_kdu_arg(info)
		self.assertEqual(region_arg, expected_kdu)

	def test_pct_to_kdu_adjust(self):
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = 'pct:20,20,100,100'
		region_parameter = RegionParameter(url_segment)
		expected_kdu = '-region \{0.2,0.2\},\{0.8,0.8\}'
		region_arg = region_parameter.to_kdu_arg(info)
		self.assertEqual(region_arg, expected_kdu)

class Test_D_SizeParameter(LorisTest):
	"""Here we construct SizeParameter objects from would-be URI slices and
	test their attributes and methods.
	"""
	def test_full(self):
		url_segment = 'full'
		expected_mode = 'full'
		expected_convert = ''
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

	def test_pct(self):
		url_segment = 'pct:50'
		expected_mode = 'pct'
		expected_pct = 50.0
		expected_convert = '-resize 50.0%'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.pct, expected_pct)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

	def test_le_0_pct_exception(self):
		url_segment = 'pct:-0.1'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)
		url_segment = 'pct:0'
		with self.assertRaises(BadSizeSyntaxException):
			SizeParameter(url_segment)

	def test_h_only(self):
		url_segment = ',100'
		expected_mode = 'pixel'
		expected_height = 100
		expected_convert = '-resize x100'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.w, None)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

	def test_w_only(self):
		url_segment = '500,'
		expected_mode = 'pixel'
		expected_width = 500
		expected_convert = '-resize 500'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, None)
		self.assertEqual(size_parameter.force_aspect, None)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

	def test_force_aspect(self):
		url_segment = '500,100'
		expected_mode = 'pixel'
		expected_width = 500
		expected_height = 100
		expected_convert = '-resize 500x100!'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.force_aspect, True)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

	def test_do_not_force_aspect(self):
		url_segment = '!500,100'
		expected_mode = 'pixel'
		expected_width = 500
		expected_height = 100
		expected_convert = '-resize 500x100'
		size_parameter = SizeParameter(url_segment)
		self.assertEqual(size_parameter.w, expected_width)
		self.assertEqual(size_parameter.h, expected_height)
		self.assertEqual(size_parameter.force_aspect, False)
		self.assertEqual(size_parameter.mode, expected_mode)
		self.assertEqual(size_parameter.to_convert_arg(), expected_convert)

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

	#TODO: do we need tests about up-sampling?

class Test_E_RotationParameter(LorisTest):
	"""Here we construct RotationParameter objects from would-be URI slices and
	test their attributes and methods.
	"""
	def test_rotation_0(self):
		url_segment = '0'
		expected_rotation = 0
		expected_kdu_arg = ''
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_convert_arg(), expected_kdu_arg)

	def test_rotation_neg_75(self):
		url_segment = '-75'
		expected_rotation = -90
		expected_kdu_arg = '-rotate -90'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_convert_arg(), expected_kdu_arg)

	def test_rotation_91(self):
		url_segment = '91'
		expected_rotation = 90
		expected_kdu_arg = '-rotate 90'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_convert_arg(), expected_kdu_arg)

	def test_rotation_314(self):
		url_segment = '314'
		expected_rotation = 270
		expected_kdu_arg = '-rotate 270'
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_convert_arg(), expected_kdu_arg)

	def test_rotation_315(self):
		url_segment = '315'
		expected_rotation = 360
		expected_kdu_arg = ''
		rotation_parameter = RotationParameter(url_segment)
		self.assertEqual(rotation_parameter.nearest_90, expected_rotation)
		self.assertEqual(rotation_parameter.to_convert_arg(), expected_kdu_arg)

class Test_F_Utilities(LorisTest):
	"""Here we exercise the shell utilities and make sure they work.
	"""
	def test_convert(self):
		# convert
		self.assertTrue(path.exists(self.app.convert_cmd))

		convert_version = self.app.convert_cmd + ' -version'
		proc = subprocess.Popen(convert_version, shell=True, \
				stderr=subprocess.PIPE, stdout=subprocess.PIPE)
		exit_status = proc.wait()

		stdout.write('\n')
		for line in proc.stdout:
			stdout.write(line)
		for line in proc.stderr:
			stderr.write(line)
		stderr.write('\n')
		self.assertEqual(exit_status, 0)


	def test_kdu(self):
		# kdu_expand
		self.assertTrue(path.exists(self.app.kdu_expand_cmd))
		kdu_v = self.app.kdu_expand_cmd + ' -v'

		proc = subprocess.Popen(kdu_v, shell=True, \
			stderr=subprocess.PIPE, stdout=subprocess.PIPE)
		exit_status = proc.wait()

		stdout.write('\n')
		for line in proc.stdout:
			stdout.write(line)
		for line in proc.stderr:
			stderr.write(line)
		stderr.write('\n')
		self.assertEqual(exit_status, 0)

class Test_G_ContentNegotiation(LorisTest):
	"""Here we make requests for different content types using both HTTP headers
	and poor-mans conneg (via file-like extensions).
	"""
	def test_info(self):
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info.xml')
		self.assertEqual(resp.headers.get('content-type'), 'text/xml')

		headers = Headers()
		headers.add('accept', 'text/xml')
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info', headers=headers)
		self.assertEqual(resp.headers.get('content-type'), 'text/xml')

		resp = self.client.get('/pudl0001/4609321/s42/00000004/info.json')
		self.assertEqual(resp.headers.get('content-type'), 'text/json')

		headers.add('accept', 'text/json')
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info', headers=headers)
		self.assertEqual(resp.headers.get('content-type'), 'text/json')


	def test_info_default(self):
		"""Asking for unsupported or no format returns the default"""
		headers = Headers()
		
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info.txt')
		self.assertEqual(resp.headers.get('content-type'), 'text/json')
		self.assertEquals(resp.status_code, 200)

		headers.clear()
		headers.add('accept', 'text/plain')
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info', headers=headers)
		self.assertEqual(resp.headers.get('content-type'), 'text/json')
		self.assertEquals(resp.status_code, 200)

		headers.clear()
		resp = self.client.get('/pudl0001/4609321/s42/00000004/info')
		self.assertEqual(resp.headers.get('content-type'), 'text/json')
		self.assertEquals(resp.status_code, 200)


	def test_img(self):
		resp = self.client.get('/pudl0001/4609321/s42/00000004/full/full/0/native.jpg')
		self.assertEqual(resp.headers.get('content-type'), 'image/jpeg')

		headers = Headers()
		headers.add('accept', 'image/jpeg')
		resp = self.client.get('/pudl0001/4609321/s42/00000004/full/pct:10/0/native', headers=headers)
		self.assertEqual(resp.headers.get('content-type'), 'image/jpeg')

		resp = self.client.get('/pudl0001/4609321/s42/00000004/full/pct:10/0/native.png')
		self.assertEqual(resp.headers.get('content-type'), 'image/png')

		headers.clear()
		headers.add('accept', 'image/png')
		resp = self.client.get('/pudl0001/4609321/s42/00000004/full/pct:10/0/native', headers=headers)
		self.assertEqual(resp.headers.get('content-type'), 'image/png')


class Test_H_Caching(LorisTest):
	"""Here we make requests for different content types using both HTTP headers
	and poor-mans conneg (file-like extensions).
	"""

	def test_cache_px_only(self):
		self.app.cache_px_only = True
		img = self.app._resolve_identifier(self.test_jp2_id)
		info = ImgInfo.fromJP2(img, self.test_jp2_id)
		url_segment = 'pct:20,20,100,100'
		region_parameter = RegionParameter(url_segment)
		try:
			region_arg = region_parameter.to_kdu_arg(info)
		except PctRegionException as e:
			self.assertEquals(e.new_region_param.url_value, '543,720,2717,3600')
			expected_kdu = '-region \{0.2,0.19985277880014722120\},\{0.8,0.80014722119985277880\}'
			self.assertEquals(e.new_region_param.to_kdu_arg(info), expected_kdu)

	def test_img_caching(self):
		url = '/pudl0033/2008/0132/00000001/0,0,256,256/full/0/color.jpg'
		resp = self.client.get(url)
		self.assertEquals(resp.status_code, 200)
		self.assertTrue(resp.headers.has_key('last-modified'))

		headers = Headers()
		yesterday = http_date(datetime.utcnow() - timedelta(days=1))
		headers.add('if-modified-since', yesterday)
		resp = self.client.get(url, headers=headers)
		self.assertEquals(resp.status_code, 304)

		headers.clear()
		tomorrow = http_date(datetime.utcnow() + timedelta(days=1))
		headers.add('if-modified-since', tomorrow)
		resp = self.client.get(url, headers=headers)
		self.assertEquals(resp.status_code, 200)


	def test_info_caching(self):
		url = '/pudl0033/2008/0132/00000001/info.json'
		resp = self.client.get(url)
		self.assertEquals(resp.status_code, 200)
		self.assertTrue(resp.headers.has_key('last-modified'))

		headers = Headers()
		yesterday = http_date(datetime.utcnow() - timedelta(days=1))
		headers.add('if-modified-since', yesterday)
		resp = self.client.get(url, headers=headers)
		self.assertEquals(resp.status_code, 304)

		headers.clear()
		tomorrow = http_date(datetime.utcnow() + timedelta(days=1))
		headers.add('if-modified-since', tomorrow)
		resp = self.client.get(url, headers=headers)
		self.assertEquals(resp.status_code, 200)

class Test_I_ResultantImg(LorisTest):
	"""Here we make requests and assertions about the resultant image's size.
	"""
	def test_full_full(self):
		dims = (2717,3600)
		uri = '/' + self.test_jp2_id + '/full/full/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_100_w(self):
		dims = (100,132)
		uri = '/' + self.test_jp2_id + '/full/100,/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_100_h(self):
		dims = (75,100)
		uri = '/' + self.test_jp2_id + '/full/,100/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_pct50(self):
		dims = (1359,1800)
		uri = '/' + self.test_jp2_id + '/full/pct:50/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_150_75(self):
		dims = (150,75)
		uri = '/' + self.test_jp2_id + '/full/150,75/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_150_75_preserved(self):
		dims = (57,75)
		uri = '/' + self.test_jp2_id + '/full/!150,75/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_full(self):
		dims = (100,200)
		uri = '/' + self.test_jp2_id + '/10,10,100,200/full/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_100_w(self):
		dims = (100,167)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/100,/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_100_h(self):
		dims = (60,100)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/,100/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_pct50(self):
		dims = (75,125)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/pct:50/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_150_75(self):
		dims = (150,75)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/150,75/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_150_75_preserve(self):
		dims = (45,75)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/!150,75/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_upsample(self):
		dims = (2989, 3960)
		uri = '/' + self.test_jp2_id + '/full/pct:110/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_upsample_w(self):
		dims = (2989, 3960)
		uri = '/' + self.test_jp2_id + '/full/2989,/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_full_upsample_h(self):
		dims = (2989, 3960)
		uri = '/' + self.test_jp2_id + '/full/,3960/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_upsample(self):
		dims = (165, 275)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/pct:110/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_upsample_w(self):
		dims = (165, 275)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/165,/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_region_upsample_h(self):
		dims = (165, 275)
		uri = '/' + self.test_jp2_id + '/10,10,150,250/,275/0/native.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def tile_gen(self, img_width, img_height, tile_size):
		"""Generates two-tuples:
		[0]: a string in the IIIF region request format, i.e. 'x,y,w,h'.
		[1]: a two-tuple with the expected actual resultant image width and height,
		compensating for the tiles at the far right and bottom, which might not be
		square. Tiles go from left to right, top to bottom.
		"""
		cy = 0
		y = 0
		while y <= img_height:
			actual_h = min(img_height-(cy*(tile_size + 1)), tile_size)
			cx = 0
			x = 0 
			while x <= img_width:
				actual_w = min(img_width-(cx*(tile_size + 1)), tile_size)
				region = ','.join(map(str, (x, y, tile_size, tile_size)))

				yield (region, (actual_w, actual_h))

				x += tile_size + 1
				cx += 1
			y += tile_size + 1
			cy += 1


	def test_region_precision(self):
		"""Make a table of tiles (left to right, top to bottom) at various 
		request sizes and check the actual size of each tile. If an image is off
		by one or two pixels, it's likely a decimal precision issue (which can be 
		increased in the conf file). Otherwise it's something else.
		"""
		ident = self.test_jp2_1_id
		jp2 = self.app._resolve_identifier(ident)
		info = ImgInfo.fromJP2(jp2, ident)
		test_sizes = [256,512,1024,2048]
		f_name = ''
		for size in test_sizes:
			for tile in self.tile_gen(info.width, info.height, size):
				uri = '/' + self.test_jp2_1_id + '/' + tile[0] + '/full/0/native.jpg'
				resp = self.client.get(uri)
				f_name = path.join(self.app.tmp_dir, 'result.jpg')
				f = open(f_name, 'w')
				f.write(resp.data)
				f.close()
				dims = self.get_jpeg_dimensions(f_name)
				self.assertEquals(dims, tile[1])
		remove(f_name)

class Test_J_SeaDragonExtension(LorisTest):
	"""Here we test for the Seadragon feature.
	"""
	def test_dzi_xml(self):
		resp = self.client.get('/pudl0001/4609321/s42/00000004.xml')
		dom = parseString(resp.data)
		# info is the root
		dE = dom.documentElement
		self.assertEqual(dE.tagName, 'Image')
		self.assertEqual(dE.getAttribute('Format'), 'jpg')
		self.assertEqual(dE.getAttribute('Overlap'), '0')
		self.assertEqual(int(dE.getAttribute('TileSize')), self.app.dz_tile_size)

		sE = dE.getElementsByTagName('Size')[0]
		self.assertEqual(sE.getAttribute('Height'), '3600')
		self.assertEqual(sE.getAttribute('Width'), '2717')

	# one where we have tiles
	def test_dzi_tile_scaling_tiled_size(self):
		dims = (self.app.dz_tile_size, self.app.dz_tile_size)
		uri = '/' + self.test_jp2_id + '_files/9/0_0.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)

	def test_dzi_tile_scaling_not_tiled_size(self):
		dims = (170,225)
		uri = '/' + self.test_jp2_id + '_files/8/0_0.jpg'
		result_dims = self._dims_from_uri(uri)
		self.assertEquals(result_dims, dims)



if __name__ == "__main__":

	tl = unittest.TestLoader()
	test_suites = []
	
	# These should be in a reasonably useful order.
	# If we can't resolve ids to images
	test_suites.append(tl.loadTestsFromTestCase(Test_A_ResolveId))
	# we can't get extract information from them (like dimensions)
	test_suites.append(tl.loadTestsFromTestCase(Test_B_InfoExtraction))
	# and if we can't get the dimensions of an image we can't translate
	# IIIF URI segments into commands
	test_suites.append(tl.loadTestsFromTestCase(Test_C_RegionParameter))
	test_suites.append(tl.loadTestsFromTestCase(Test_D_SizeParameter))
	test_suites.append(tl.loadTestsFromTestCase(Test_E_RotationParameter))
	#. We can't execute those commands if we can't make the shell utilities 
	# work:
	test_suites.append(tl.loadTestsFromTestCase(Test_F_Utilities))	
	# and therefore can't make images, and can't ask for them
	test_suites.append(tl.loadTestsFromTestCase(Test_G_ContentNegotiation))
	test_suites.append(tl.loadTestsFromTestCase(Test_H_Caching))
	# or test that the output is the expectant size, rotation, etc.
	test_suites.append(tl.loadTestsFromTestCase(Test_I_ResultantImg))
	# And Seadragon is cool
	test_suites.append(tl.loadTestsFromTestCase(Test_J_SeaDragonExtension))
	#.
	meta_suite = unittest.TestSuite(test_suites)
	unittest.TextTestRunner(verbosity=2).run(meta_suite)
	