#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
Superclass for integration tests.
'''
from __future__ import absolute_import

import unittest
from os import path, listdir, unlink
from shutil import rmtree
from logging import getLogger

try:
    from cStringIO import StringIO
except ImportError:  # Python 3
    from io import StringIO

from PIL.ImageFile import Parser
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from loris.webapp import get_debug_config, Loris

logger = getLogger(__name__)

class LorisTest(unittest.TestCase):

    def build_client_from_config(self, config):
        self.app = Loris(config)
        self.client = Client(self.app, BaseResponse)

    def setUp(self):
        self.URI_BASE = 'http://localhost'

        #for SimpleHTTPResolver
        self.SRC_IMAGE_CACHE = '/tmp/loris/cache/src_images'

        # create an instance of the app here that we can use in tests
        # see http://werkzeug.pocoo.org/docs/test/
        config = get_debug_config('kdu')
        config['logging']['log_level'] = 'INFO'
        self.build_client_from_config(config)

        # constant info about test images.
        self.test_img_dir = path.join(path.abspath(path.dirname(__file__)), 'img')
        self.test_img_dir2 = path.join(path.abspath(path.dirname(__file__)), 'img2')
        test_json_dir = path.join(path.abspath(path.dirname(__file__)), 'json')
        test_icc_dir = path.join(path.abspath(path.dirname(__file__)), 'icc')

        self.test_jp2_color_fp = path.join(self.test_img_dir,'01','02','0001.jp2')
        self.test_jp2_color_info_fp = path.join(test_json_dir,'01','02','0001.jp2','info.json')
        self.test_jp2_color_fmt = 'jp2'
        self.test_jp2_color_id = '01%2F02%2F0001.jp2'
        self.test_jp2_color_uri = '%s/%s' % (self.URI_BASE, self.test_jp2_color_id)
        self.test_jp2_color_dims = (5906,7200)
        self.test_jp2_color_levels = 6
        self.test_jp2_color_tiles = [
            { "width": 256, "scaleFactors": [1,2,4,8,16,32,64] }
        ]
        self.test_jp2_color_sizes =  [
            { "height": 113, "width": 93 },
            { "height": 225, "width": 185 },
            { "height": 450, "width": 370 },
            { "height": 900, "width": 739 },
            { "height": 1800, "width": 1477 },
            { "height": 3600, "width": 2953 },
            { "height": 7200, "width": 5906 }
        ]

        self.test_jp2_gray_fp = path.join(self.test_img_dir,'01','02','gray.jp2')
        self.test_jp2_gray_fmt = 'jp2'
        self.test_jp2_gray_id = '01%2F02%2Fgray.jp2'
        self.test_jp2_gray_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_gray_id)
        self.test_jp2_gray_dims = (2477,3200) # w,h
        self.test_jp2_gray_sizes =  [
            { "height": 50, "width": 39 },
            { "height": 100, "width": 78 },
            { "height": 200, "width": 155 },
            { "height": 400, "width": 310 },
            { "height": 800, "width": 620 },
            { "height": 1600, "width": 1239 },
            { "height": 3200, "width": 2477 }
        ]
        self.test_jp2_gray_tiles = [
            { "width": 256, "scaleFactors": [1,2,4,8,16,32,64] }
        ]

        self.test_jpeg_fp = path.join(self.test_img_dir,'01','03','0001.jpg')
        self.test_jpeg_fmt = 'jpg'
        self.test_jpeg_id = '01%2F03%2F0001.jpg'
        self.test_jpeg_uri = '%s/%s' % (self.URI_BASE,self.test_jpeg_id)
        self.test_jpeg_dims = (3600,2987) # w,h
        self.test_jpeg_sizes = []

        self.test_jpeg_grid_fp = path.join(self.test_img_dir, 'black_white_grid.jpg')
        self.test_jpeg_grid_id = 'black_white_grid.jpg'
        self.test_jpeg_grid_dims = (120, 120)

        self.test_tiff_fp = path.join(self.test_img_dir,'01','04','0001.tif')
        self.test_tiff_fmt = 'tif'
        self.test_tiff_id = '01%2F04%2F0001.tif'
        self.test_tiff_uri = '%s/%s' % (self.URI_BASE,self.test_tiff_id)
        self.test_tiff_dims = (839,1080)
        self.test_tiff_sizes = []

        self.test_png_fp = path.join(self.test_img_dir,'henneken.png')
        self.test_png_fp2 = path.join(self.test_img_dir2,'henneken.png')
        self.test_png_fmt = 'png'
        self.test_png_id = 'henneken.png'
        self.test_png_uri = '%s/%s' % (self.URI_BASE,self.test_png_id)
        self.test_png_dims = (504,360) # w,h
        self.test_png_sizes = []

        self.test_altpng_id = 'foo.png'
        self.test_altpng_fp = path.join(self.test_img_dir2,'foo.png')

        self.test_jp2_with_embedded_profile_id = '47102787.jp2'
        self.test_jp2_with_embedded_profile_fp = path.join(self.test_img_dir,self.test_jp2_with_embedded_profile_id)
        self.test_jp2_embedded_profile_copy_fp = path.join(test_icc_dir,'profile.icc')
        self.test_jp2_with_embedded_profile_fmt = 'jp2'
        self.test_jp2_with_embedded_profile_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_with_embedded_profile_id)

        # A copy of 47102787.jp2, with the embedded color profile converted
        # to sRGB and saved as JPG.
        self.test_jp2_with_embedded_profile_to_srgb_jpg_fp = path.join(
            self.test_img_dir, '47102787_to_srgb.jpg'
        )

        self.test_jpeg_with_embedded_profile_id = 'jpeg_with_p3_profile.jpg'
        self.test_jpeg_with_embedded_profile_fp = path.join(self.test_img_dir, self.test_jpeg_with_embedded_profile_id)

        # A JPEG with an embedded CMYK profile.  Public domain image downloaded
        # from https://commons.wikimedia.org/wiki/File:Frog_logo_CMYK.jpg
        self.test_jpeg_with_embedded_cmyk_profile_id = 'jpeg_with_cmyk_profile.jpg'

        self.test_jp2_with_precincts_id = 'sul_precincts.jp2'
        self.test_jp2_with_precincts_fp = path.join(self.test_img_dir,self.test_jp2_with_precincts_id)
        self.test_jp2_with_precincts_fmt = 'jp2'
        self.test_jp2_with_precincts_uri = '%s/%s' % (self.URI_BASE,self.test_jp2_with_precincts_id)
        self.test_jp2_with_precincts_sizes =  [
            { "height": 93, "width": 71 },
            { "height": 186, "width": 141 },
            { "height": 372, "width": 281 },
            { "height": 743, "width": 561 },
            { "height": 1486, "width": 1122 },
            { "height": 2972, "width": 2244 },
            { "height": 5944, "width": 4488 }
        ]
        self.test_jp2_with_precincts_tiles = [
            { "width": 128, "scaleFactors": [1,2,4,8,16] },
            { "width": 256, "scaleFactors": [32,64] }
        ]

        # An ICC v2 sRGB color profile.
        # Downloaded from http://www.color.org/srgbprofiles.xalter
        self.srgb_color_profile_fp = path.join(test_icc_dir, 'sRGB2014.icc')

    def tearDown(self):
        # empty the cache
        dps = (
            self.SRC_IMAGE_CACHE,
            self.app.app_configs['img.ImageCache']['cache_dp'],
            self.app.app_configs['img_info.InfoCache']['cache_dp'],
            self.app.tmp_dp,
        )
        for dp in dps:
            if path.exists(dp):
                for node in listdir(dp):
                    p = path.join(dp, node)
                    if path.isdir(p):
                        rmtree(p)
                        logger.debug('Removed %s', p)
                    else: # TODO: make sure this covers symlinks
                        unlink(p)
                        logger.debug('Removed %s', p)
                rmtree(dp)
                logger.debug('Removed %s', dp)

    def request_image_from_client(self, request_path):
        resp = self.client.get(request_path)
        self.assertEqual(resp.status_code, 200)

        bytes = StringIO(resp.data)
        p = Parser()
        p.feed(bytes.read())
        image = p.close()
        bytes.close()

        return image
