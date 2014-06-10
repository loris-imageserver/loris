#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
Superclass for all other unit tests
'''

import unittest
from loris.webapp import create_app
from os import path, listdir, unlink
from shutil import rmtree
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse, Request
from logging import getLogger

logger = getLogger(__name__)

class LorisTest(unittest.TestCase):

	def setUp(self):
		unittest.TestCase.setUp(self)

		self.URI_BASE = 'http://localhost'
		
		# create an instance of the app here that we can use in tests
		# see http://werkzeug.pocoo.org/docs/test/
		self.app = create_app(debug=True)
		self.client = Client(self.app, BaseResponse)
		

		# constant info about test images.
		test_img_dir = path.join(path.abspath(path.dirname(__file__)), 'img')
		test_json_dir = path.join(path.abspath(path.dirname(__file__)), 'json')
		test_icc_dir = path.join(path.abspath(path.dirname(__file__)), 'icc')

		self.test_jp2_color_fp = path.join(test_img_dir,'01','02','0001.jp2')
		self.test_jp2_color_info_fp = path.join(test_json_dir,'01','02','0001.jp2','info.json')
		self.test_jp2_color_fmt = 'jp2'
		self.test_jp2_color_id = '01%2F02%2F0001.jp2'
		self.test_jp2_color_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_color_id)
		self.test_jp2_color_dims = (5906,7200) 
		self.test_jp2_color_tile_dims = (256,256)
		self.test_jp2_color_levels = 6
		self.test_jp2_color_sizes = ['5906,7200', '2953,3600', '1477,1800', '739,900', '370,450', '185,225', '93,113']

		self.test_jp2_gray_fp = path.join(test_img_dir,'01','02','gray.jp2')
		self.test_jp2_gray_fmt = 'jp2'
		self.test_jp2_gray_id = '01%2F02%2Fgray.jp2'
		self.test_jp2_gray_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_gray_id)
		self.test_jp2_gray_dims = (2477,3200) # w,h
		self.test_jp2_gray_tile_dims = (256,256) # w,h

		self.test_jpeg_fp = path.join(test_img_dir,'01','03','0001.jpg')
		self.test_jpeg_fmt = 'jpg'
		self.test_jpeg_id = '01%2F03%2F0001.jpg'
		self.test_jpeg_uri = '%s/%s' % (self.URI_BASE,self.test_jpeg_id)
		self.test_jpeg_dims = (3600,2987) # w,h
		self.test_jpeg_sizes = ["3600,2987"] # w,h

		self.test_tiff_fp = path.join(test_img_dir,'01','04','0001.tif')
		self.test_tiff_fmt = 'tif'
		self.test_tiff_id = '01%2F04%2F0001.tif'
		self.test_tiff_uri = '%s/%s' % (self.URI_BASE,self.test_tiff_id)
		self.test_tiff_dims = (839,1080)
		self.test_tiff_sizes = ["839,1080"]

		self.test_jp2_with_embedded_profile_fp = path.join(test_img_dir,'47102787.jp2')
		self.test_jp2_embedded_profile_copy_fp = path.join(test_icc_dir,'profile.icc')
		self.test_jp2_with_embedded_profile_fmt = 'jp2'
		self.test_jp2_with_embedded_profile_id = '47102787.jp2'
		self.test_jp2_with_embedded_profile_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_gray_id)

	def tearDown(self):
		unittest.TestCase.tearDown(self)
		# empty the cache
		dps = (
			self.app.app_configs['img.ImageCache']['cache_dp'],
			self.app.app_configs['img.ImageCache']['cache_links'],
			self.app.app_configs['img_info.InfoCache']['cache_dp'],
			self.app.tmp_dp
		)
		for dp in dps:
			if path.exists(dp):
				for node in listdir(dp):
					p = path.join(dp, node)
					if path.isdir(p):
						rmtree(p)
						logger.debug('Removed %s' % (p,))
					else: # TODO: make sure this covers symlinks
						unlink(p)
						logger.debug('Removed %s' % (p,))
				rmtree(dp)
				logger.debug('Removed %s' % (dp,))

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
