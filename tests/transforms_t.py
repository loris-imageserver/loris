import unittest
import operator

import pytest
from PIL.Image import DecompressionBombError

from loris import transforms
from loris.loris_exception import ConfigError
from loris.webapp import get_debug_config
from tests import loris_t


class ColorConversionMixin:
    """
    Adds a helper method for testing that a transformer can edit the
    embedded color profile on an image.
    """

    def _assert_can_edit_embedded_color_profile(self, ident, transformer, debug_config='kdu'):
        request_path = '/%s/full/full/0/default.jpg' % ident

        image_orig = self.request_image_from_client(request_path)

        # Set up an instance of the client with color profile editing.
        # We need to disable caching so the new request doesn't pick up
        # the cached image.
        config = get_debug_config(debug_config)
        config['transforms'][transformer]['map_profile_to_srgb'] = True
        config['transforms'][transformer]['srgb_profile_fp'] = self.srgb_color_profile_fp
        config['loris.Loris']['enable_caching'] = False
        self.build_client_from_config(config)

        image_converted = self.request_image_from_client(request_path)

        # Now check that the image pixels have been edited -- this means
        # that the color profile has changed.  Because image conversion
        # isn't stable across platforms, this is the best we can do for now.
        # TODO: Maybe try image hashing here?
        self.assertNotEqual(image_orig.histogram(), image_converted.histogram())


class _ResizingTestMixin:
    """
    Tests that image resizing works correctly.
    """
    def test_resizing_image_with_fixed_width(self):
        request_path = '/%s/full/300,/0/default.jpg' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.width == 300

    def test_resizing_image_with_fixed_height(self):
        request_path = '/%s/full/,300/0/default.jpg' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.height == 300

    def test_resizing_image_with_best_fit(self):
        request_path = '/%s/full/300,300/0/default.jpg' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.width <= 300
        assert image.height <= 300

    def test_resizing_image_with_fixed_dimensions(self):
        request_path = '/%s/full/420,180/0/default.jpg' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.width <= 420
        assert image.height <= 180


class ExampleTransformer(transforms._AbstractTransformer):
    pass


class Test_AbstractTransformer(object):

    def test_missing_transform_raises_not_implemented_error(self):
        e = ExampleTransformer(config={
            'target_formats': [],
            'dither_bitonal_images': '',
        })
        with pytest.raises(NotImplementedError) as err:
            e.transform(target_fp=None, image_request=None, image_info=None)
        assert str(err.value) == 'transform() not implemented for ExampleTransformer'

    @pytest.mark.parametrize('config', [
        {'map_profile_to_srgb': True},
        {'map_profile_to_srgb': True, 'srgb_profile_fp': ''},
        {'map_profile_to_srgb': True, 'srgb_profile_fp': None},
    ])
    def test_bad_srgb_profile_fp_is_configerror(self, config):
        with pytest.raises(ConfigError) as err:
            ExampleTransformer(config=config)
        assert 'you need to give the path to an sRGB color profile' in str(err.value)

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
        assert 'you need to install Pillow with LittleCMS support' in str(err.value)


class UnitTest_KakaduJP2Transformer(unittest.TestCase):

    def test_init(self):
        config = {'kdu_expand': '', 'num_threads': 4, 'kdu_libs': '',
                  'map_profile_to_srgb': False, 'mkfifo': '', 'tmp_dp': '/tmp/loris/tmp',
                  'srgb_profile_fp': '', 'target_formats': [], 'dither_bitonal_images': ''}
        kdu_transformer = transforms.KakaduJP2Transformer(config)
        self.assertEqual(kdu_transformer.transform_timeout, 120)
        config['timeout'] = 100
        kdu_transformer = transforms.KakaduJP2Transformer(config)
        self.assertEqual(kdu_transformer.transform_timeout, 100)


class Test_KakaduJP2Transformer(loris_t.LorisTest,
                                ColorConversionMixin,
                                _ResizingTestMixin):

    def setUp(self):
        super(Test_KakaduJP2Transformer, self).setUp()
        self.ident = self.test_jp2_color_id

    def test_allows_jp2_upsample(self):
        # Makes a request rather than building everything from scratch
        ident = self.test_jp2_color_id
        request_path = '/%s/full/pct:110/0/default.jpg' % (ident,)
        image = self.request_image_from_client(request_path)

        expected_dims = tuple(int(d*1.10) for d in self.test_jp2_color_dims)

        self.assertEqual(expected_dims, image.size)

    def test_can_edit_embedded_color_profile(self):
        self._assert_can_edit_embedded_color_profile(
            ident=self.test_jp2_with_embedded_profile_id,
            transformer='jp2',
            debug_config='kdu'
        )

    def test_hung_process_gets_terminated(self):
        config = get_debug_config('kdu')
        config['transforms']['jp2']['kdu_expand'] = '/dev/null'
        config['transforms']['jp2']['timeout'] = 1
        self.build_client_from_config(config)
        ident = self.test_jp2_color_id
        request_path = '/%s/full/full/0/default.jpg' % ident
        response = self.client.get(request_path)
        assert response.status_code == 500
        assert 'JP2 transform process timed out' in response.data.decode('utf8')


class Test_OPJ_JP2Transformer(loris_t.LorisTest, ColorConversionMixin):

    def setUp(self):
        super(Test_OPJ_JP2Transformer, self).setUp()
        self.ident = self.test_jp2_color_id

    def test_can_edit_embedded_color_profile(self):
        # By default, LorisTest uses the Kakadu transformer.  Switch to the
        # OPENJPEG transformer before we get the reference image.
        config = get_debug_config('opj')
        self.build_client_from_config(config)

        self._assert_can_edit_embedded_color_profile(
            ident=self.test_jp2_with_embedded_profile_id,
            transformer='jp2',
            debug_config='opj'
        )

    def test_hung_process_gets_terminated(self):
        config = get_debug_config('opj')
        config['transforms']['jp2']['opj_decompress'] = '/dev/null'
        config['transforms']['jp2']['timeout'] = 1
        self.build_client_from_config(config)
        ident = self.test_jp2_color_id
        request_path = '/%s/full/full/0/default.jpg' % ident
        response = self.client.get(request_path)
        assert response.status_code == 500
        assert 'JP2 transform process timed out' in response.data.decode('utf8')


class Test_PILTransformer(loris_t.LorisTest,
                          ColorConversionMixin,
                          _ResizingTestMixin):

    def setUp(self):
        super(Test_PILTransformer, self).setUp()
        self.ident = self.test_jpeg_id

    def test_png_rotate_has_alpha_transparency(self):
        ident = 'test.png'
        rotate = '45'
        request_path = '/%s/full/full/%s/default.png' % (ident,rotate)
        image = self.request_image_from_client(request_path)

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
        return map(alpha_getter, image.getdata())

    def test_can_edit_embedded_color_profile(self):
        self._assert_can_edit_embedded_color_profile(
            ident=self.test_jpeg_with_embedded_profile_id,
            transformer='jpg'
        )

    def test_editing_embedded_color_profile_failure_is_not_error(self):
        ident = self.test_jpeg_with_embedded_cmyk_profile_id
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

        # Now fetch the image, and check that it remains unmodified.
        self.assertEqual(image_orig.histogram(), image_converted.histogram())

    def test_cropping_image_top_left_corner(self):
        ident = self.test_jpeg_grid_id
        request_path = '/%s/pct:0,0,45,45/full/0/default.jpg' % ident
        image = self.request_image_from_client(request_path)

        # If we select just the top left-hand corner, we expect that all
        # the pixels will be black.
        assert image.getcolors() == [(2916, (0, 0, 0))]

    def test_cropping_image_top_right_corner(self):
        ident = self.test_jpeg_grid_id
        request_path = '/%s/pct:55,0,50,50/full/0/default.jpg' % ident
        image = self.request_image_from_client(request_path)

        # If we select just the top right-hand corner, we expect that all
        # the pixels will be white.  Note that we select slightly beyond
        # halfway to avoid getting JPEG artefacts mixed in here.
        assert image.getcolors() == [(3240, (255, 255, 255))]

    def test_rotation_and_mirroring(self):
        ident = self.test_jpeg_grid_id

        # If we request the image without rotation, we expect to see a
        # black pixel in the top left-hand corner.
        request_path = '/%s/full/full/0/default.jpg' % ident
        image = self.request_image_from_client(request_path)
        assert image.getpixel((0, 0)) == (0, 0, 0)

        # Now if we rotate the image through 90 degrees, we'll see a
        # white pixel.
        request_path = '/%s/full/full/90/default.jpg' % ident
        image = self.request_image_from_client(request_path)
        assert image.getpixel((0, 0)) == (255, 255, 255)

        # Rotation through 180 degrees gets us a red pixel
        request_path = '/%s/full/full/180/default.jpg' % ident
        image = self.request_image_from_client(request_path)
        assert image.getpixel((0, 0)) == (254, 0, 0)

        # Rotation through 180 degrees with mirroring gets us a white pixel
        request_path = '/%s/full/full/!180/default.jpg' % ident
        image = self.request_image_from_client(request_path)
        assert image.getpixel((0, 0)) == (255, 255, 255)

    def test_can_request_gif_format(self):
        ident = self.test_jpeg_id
        request_path = '/%s/full/full/0/default.gif' % ident
        image = self.request_image_from_client(request_path)
        assert image.format == 'GIF'

    def test_can_request_webp_format(self):
        ident = self.test_jpeg_id
        request_path = '/%s/full/full/0/default.webp' % ident
        image = self.request_image_from_client(request_path)
        assert image.format == 'WEBP'

    def test_can_request_tif_format(self):
        ident = self.test_jpeg_id
        request_path = '/%s/full/full/0/default.tif' % ident
        image = self.request_image_from_client(request_path)
        assert image.format == 'TIFF'

    def test_convert_to_bitonal_with_rotation_is_mode_LA(self):
        request_path = '/%s/full/full/45/bitonal.png' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.mode == 'LA'

    def test_convert_to_gray_with_rotation_is_mode_LA(self):
        request_path = '/%s/full/full/45/gray.png' % self.ident
        image = self.request_image_from_client(request_path)
        assert image.mode == 'LA'

    def test_convert_to_gray_with_no_alpha_is_mode_L(self):
        request_path = '/%s/full/full/0/gray.jpg' % self.test_jpeg_id
        image = self.request_image_from_client(request_path)
        assert image.mode == 'L'

    def test_jpeg_encoded_tif_can_be_retrieved(self):
        # This checks an issue with Pillow where attempting to load
        # JPEG-compressed TIFFs.  The test file is taken from the test case
        # described in https://github.com/python-pillow/Pillow/issues/2926.
        #
        # See https://github.com/loris-imageserver/loris/issues/405
        request_path = '/ycbcr-jpeg.tiff/full/full/0/default.jpg'
        image = self.request_image_from_client(request_path)

    def test_can_transform_transparent_png_as_nontransparent_format(self):
        ident = 'png_with_transparency.png'
        request_path = '/%s/full/full/0/default.jpg' % ident
        self.request_image_from_client(request_path)

    def test_respects_pil_max_image_pixels(self):
        config = get_debug_config('kdu')
        config['transforms']['pil_max_image_pixels'] = 1
        self.build_client_from_config(config)
        with pytest.raises(DecompressionBombError):
            request_path = '/%s/full/300,300/0/default.jpg' % self.ident
            self.request_image_from_client(request_path)
