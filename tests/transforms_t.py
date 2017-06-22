#-*- coding: utf-8 -*-
from cStringIO import StringIO
import unittest
import loris_t, operator, itertools
from PIL.ImageFile import Parser
from loris import transforms

"""
Transformer tests. These right now these work with the kakadu and PIL
transformers. More should be added when different libraries/scenarios are added.

To run this test on its own, do:

$ python -m unittest tests.transforms_t

from the `/loris` (not `/loris/loris`) directory.
"""


class Test_AbstractTransformer(unittest.TestCase):

    def test_missing_transform_raises_not_implemented_error(self):
        class ExampleTransformer(transforms._AbstractTransformer):
            pass

        e = ExampleTransformer(config={
            'target_formats': [],
            'dither_bitonal_images': '',
        })
        with self.assertRaises(NotImplementedError) as cm:
            e.transform(src_fp=None, target_fp=None, image_request=None)
        self.assertEqual(
            cm.exception.message,
            'transform() not implemented for ExampleTransformer')


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
        resp = self.client.get(request_path)

        self.assertEqual(resp.status_code, 200)

        image = None
        bytes = StringIO(resp.data)
        p = Parser()
        p.feed(bytes.read()) # all in one gulp!
        image = p.close()
        bytes.close()
        expected_dims = tuple(int(d*1.10) for d in self.test_jp2_color_dims)

        self.assertEqual(expected_dims, image.size)


class Test_PILTransformer(loris_t.LorisTest):

    def test_png_rotate_has_alpha_transparency(self):
        ident = 'test.png'
        rotate = '45'
        request_path = '/%s/full/full/%s/default.png' % (ident,rotate)
        resp = self.client.get(request_path)

        self.assertEqual(resp.status_code, 200)

        image = None
        bytes = StringIO(resp.data)
        p = Parser()
        p.feed(bytes.read()) # all in one gulp!
        image = p.close()
        bytes.close()

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


def suite():
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_AbstractTransformer, 'test'))
    test_suites.append(unittest.makeSuite(UnitTest_KakaduJP2Transformer, 'test'))
    test_suites.append(unittest.makeSuite(Test_KakaduJP2Transformer, 'test'))
    test_suites.append(unittest.makeSuite(Test_PILTransformer, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
