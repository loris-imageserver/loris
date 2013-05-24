#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
Superclass for all other unit tests
'''

import unittest
from loris.webapp import create_app
from os import path, listdir
from shutil import rmtree
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse, Request

class LorisTest(unittest.TestCase):
	def setUp(self):
		unittest.TestCase.setUp(self)
		# create an instance of the app here that we can use in tests
		# see http://werkzeug.pocoo.org/docs/test/
		self.app = create_app(debug=True)
		self.client = Client(self.app, BaseResponse)

		# constant info about test images.
		test_img_dir = path.join(path.abspath(path.dirname(__file__)), 'img')

		self.test_jp2_color_fp = path.join(test_img_dir,'01','02','0001.jp2')
		self.test_jp2_color_fmt = 'jp2'
		self.test_jp2_color_id = '01%2F02%2F0001.jp2'
		self.test_jp2_color_dims = (3188,3600) # w,h
		self.test_jp2_color_tile_dims = (256,256) # w,h
		self.test_jp2_color_levels = 5 # w,h

		self.test_jp2_grey_fp = path.join(test_img_dir,'01','02','grey.jp2')
		self.test_jp2_grey_fmt = 'jp2'
		self.test_jp2_grey_id = '01%2F02%2Fgrey.jp2'
		self.test_jp2_grey_dims = (2477,3200) # w,h
		self.test_jp2_grey_tile_dims = (256,256) # w,h

		self.test_jpeg_fp = path.join(test_img_dir,'01','03','0001.jpg')
		self.test_jpeg_fmt = 'jpg'
		self.test_jpeg_id = '01%2F03%2F0001.jpg'
		self.test_jpeg_dims = (3600,2987) # w,h

		self.test_tiff_fp = path.join(test_img_dir,'01','04','0001.tif')
		self.test_tiff_fmt = 'tif'
		self.test_tiff_id = '01%2F04%2F0001.tif'
		self.test_tiff_dims = (839,1080)

	def tearDown(self):
		unittest.TestCase.tearDown(self)
		# empty the cache
		cache_dp = self.app.config['loris.Loris']['cache_dp']
		for d in listdir(cache_dp):
			rmtree(path.join(cache_dp, d))
		rmtree(cache_dp)

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

	# def dims_from_uri(self, uri):
	# 	"""Make a request, save it out, and return the dimensions.
	# 	"""
	# 	resp = self.client.get(uri)
	# 	fp = path.join(loris.app.TMP, 'result.jpg')
	# 	f = open(fp, 'w')
	# 	f.write(resp.data)
	# 	f.close()
	# 	return self.get_jpeg_dimensions(fp)