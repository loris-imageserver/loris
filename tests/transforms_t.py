#-*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest
import operator, itertools

import pytest

from loris import transforms
from loris.loris_exception import ConfigError
from loris.webapp import get_debug_config
from tests import loris_t

"""
Transformer tests. These right now these work with the kakadu and PIL
transformers. More should be added when different libraries/scenarios are added.

To run this test on its own, do:

$ python -m unittest tests.transforms_t

from the `/loris` (not `/loris/loris`) directory.
"""

class ExampleTransformer(transforms._AbstractTransformer):
    pass


class Test_AbstractTransformer(object):

    def test_missing_transform_raises_not_implemented_error(self):
        e = ExampleTransformer(config={
            'target_formats': [],
            'dither_bitonal_images': '',
        })
        with pytest.raises(NotImplementedError) as err:
            e.transform(src_fp=None, target_fp=None, image_request=None)
        assert err.value.message == 'transform() not implemented for ExampleTransformer'

    @pytest.mark.parametrize('config', [
        {'map_profile_to_srgb': True},
        {'map_profile_to_srgb': True, 'srgb_profile_fp': ''},
        {'map_profile_to_srgb': True, 'srgb_profile_fp': None},
    ])
    def test_bad_srgb_profile_fp_is_configerror(self, config):
        with pytest.raises(ConfigError) as err:
            ExampleTransformer(config=config)
        assert 'you need to give the path to an sRGB color profile' in err.value.message

    def test_missing_littlecms_with_srgb_conversion_is_configerror(self):
        try:
            transforms.has_imagecms = False
            with pytest.raises(ConfigError) as err:
                ExampleTransformer(config={
                    'map_profile_to_srgb': True,
                    'srgb_profile_fp': '/home/profiles/srgb.icc'
                })
        finally:
            transforms.has_imagecms = True
        assert 'you need to install Pillow with LittleCMS support' in err.value.message


class UnitTest_KakaduJP2Transformer(unittest.TestCase):

    def test_init(self):
        config = {'kdu_expand': '', 'num_threads': 4, 'kdu_libs': '',
                  'map_profile_to_srgb': True, 'mkfifo': '', 'tmp_dp': '/tmp/loris/tmp',
                  'srgb_profile_fp': '', 'target_formats': [], 'dither_bitonal_images': ''}
        kdu_transformer = transforms.KakaduJP2Transformer(config)
        self.assertEqual(kdu_transformer.transform_timeout, 120)
        config['timeout'] = 100
        kdu_transformer = transforms.KakaduJP2Transformer(config)
        self.assertEqual(kdu_transformer.transform_timeout, 100)


class Test_KakaduJP2Transformer(loris_t.LorisTest):

    def test_allows_jp2_upsample(self):
        # Makes a request rather than building everything from scratch
        ident = self.test_jp2_color_id
        request_path = '/%s/full/pct:110/0/default.jpg' % (ident,)
        image = self.request_image_from_client(request_path)

        expected_dims = tuple(int(d*1.10) for d in self.test_jp2_color_dims)

        self.assertEqual(expected_dims, image.size)

    def test_can_edit_embedded_color_profile(self):
        ident = self.test_jp2_with_embedded_profile_id
        request_path = '/%s/full/full/0/default.jpg' % ident

        image_orig = self.request_image_from_client(request_path)

        # Set up an instance of the client with color profile editing.
        # We need to disable caching so the new request doesn't pick up
        # the cached image.
        config = get_debug_config('kdu')
        config['transforms']['jp2']['map_profile_to_srgb'] = True
        config['transforms']['jp2']['srgb_profile_fp'] = self.srgb_color_profile_fp
        config['loris.Loris']['enable_caching'] = False
        self.build_client_from_config(config)

        image_converted = self.request_image_from_client(request_path)

        # Now check that the image pixels have been edited -- this means
        # that the color profile has changed.  Because image conversion isn't
        # stable across platforms, this is the best we can do for now.
        self.assertNotEqual(image_orig.histogram(), image_converted.histogram())


class Test_PILTransformer(loris_t.LorisTest):

    def test_png_rotate_has_alpha_transparency(self):
        ident = 'test.png'
        rotate = '45'
        request_path = '/%s/full/full/%s/default.png' % (ident,rotate)
        image = self.request_image_from_client(request_path)

        # Get the alpha channel as an itertools.imap
        alpha = self.get_alpha_channel(image)

        # Instantiate transparency as False
        transparency = False

        # Loop on the alpha channel and see if we have a value of
        # 0 which means there's a transparent pixel there
        if alpha != None:
            for i in alpha:
                if i == 0:
                    transparency = True

        self.assertTrue(transparency)

    """
    Return the alpha channel as a sequence of values

    Source: http://stackoverflow.com/a/1963141/1255004
    (credit to tzot @ http://stackoverflow.com/users/6899/tzot)
    """
    def get_alpha_channel(self, image):

        # Extract the alpha band from the image
        try:
            alpha_index= image.getbands().index('A')
        except ValueError:
            return None # no alpha channel, presumably

        alpha_getter= operator.itemgetter(alpha_index)
        return itertools.imap(alpha_getter, image.getdata())

    def test_can_edit_embedded_color_profile(self):
        ident = self.test_jpeg_with_embedded_profile_id
        request_path = '/%s/full/full/0/default.jpg' % ident

        image_orig = self.request_image_from_client(request_path)

        # Set up an instance of the client with color profile editing.
        # We need to disable caching so the new request doesn't pick up
        # the cached image.
        config = get_debug_config('kdu')
        config['transforms']['jpg']['map_profile_to_srgb'] = True
        config['transforms']['jpg']['srgb_profile_fp'] = self.srgb_color_profile_fp
        config['loris.Loris']['enable_caching'] = False
        self.build_client_from_config(config)

        image_converted = self.request_image_from_client(request_path)

        # Now check that the image pixels have been edited -- this means
        # that the color profile has changed.  Because image conversion isn't
        # stable across platforms, this is the best we can do for now.
        self.assertNotEqual(image_orig.histogram(), image_converted.histogram())



def suite():
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_AbstractTransformer, 'test'))
    test_suites.append(unittest.makeSuite(Test_JP2TransformerConfig, 'test'))
    test_suites.append(unittest.makeSuite(UnitTest_KakaduJP2Transformer, 'test'))
    test_suites.append(unittest.makeSuite(Test_KakaduJP2Transformer, 'test'))
    test_suites.append(unittest.makeSuite(Test_PILTransformer, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
