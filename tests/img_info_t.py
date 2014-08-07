# img_info_t.py
#-*- coding: utf-8 -*-

from loris import img_info
from loris.constants import PROTOCOL
from os import path
from werkzeug.datastructures import Headers
import json
import loris_t


"""
Info unit and function tests. To run this test on its own, do:

$ python -m unittest -v tests.img_info_t

from the `/loris` (not `/loris/loris`) directory.
"""

class Test_B_InfoUnit(loris_t.LorisTest):
    'Tests ImageInfo constructors.'

    def test_color_jp2_info_from_image(self):
        fp = self.test_jp2_color_fp
        fmt = self.test_jp2_color_fmt
        ident = self.test_jp2_color_id
        uri = self.test_jp2_color_uri

        profile = ["http://iiif.io/api/image/2/level2.json", { 
                "formats": [ "jpg", "png", "gif" ],
                "qualities": [ 
                    "default", 
                    "bitonal", 
                    "gray", 
                    "color" 
                ],
                "supports": [ 
                    "canonical_link_header",
                    "mirroring",
                    "rotation_arbitrary",
                    "size_above_full"
                ]
            }
        ]

        formats = ["jpg", "png", "gif"]
        info = img_info.ImageInfo.from_image_file(uri, fp, fmt, formats)

        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)
        self.assertEqual(info.sizes, self.test_jp2_color_sizes)
        self.assertEqual(info.ident, uri)
        self.assertEqual(info.protocol, PROTOCOL)

    def test_precinct_jp2_tiles_from_image(self):
        formats = ["jpg", "png", "gif"]
        fp = self.test_jp2_with_precincts_fp
        fmt = self.test_jp2_with_precincts_fmt
        ident = self.test_jp2_with_precincts_id
        uri = self.test_jp2_with_precincts_uri

        info = img_info.ImageInfo.from_image_file(uri, fp, fmt, formats)

        self.assertEqual(info.tiles, self.test_jp2_with_precincts_tiles)
        self.assertEqual(info.sizes, self.test_jp2_with_precincts_sizes)

    def test_extract_icc_profile_from_jp2(self):
        fp = self.test_jp2_with_embedded_profile_fp
        fmt = self.test_jp2_with_embedded_profile_fmt
        ident = self.test_jp2_with_embedded_profile_id
        uri = self.test_jp2_with_embedded_profile_uri
        profile_copy_fp = self.test_jp2_embedded_profile_copy_fp

        info = img_info.ImageInfo.from_image_file(uri, fp, fmt)

        with open(self.test_jp2_embedded_profile_copy_fp, 'rb') as fixture_bytes:
            self.assertEqual(info.color_profile_bytes, fixture_bytes.read())

    def test_no_embedded_profile_info_color_profile_bytes_is_None(self):
        fp = self.test_jp2_color_fp
        fmt = self.test_jp2_color_fmt
        ident = self.test_jp2_color_id
        uri = self.test_jp2_color_uri

        info = img_info.ImageInfo.from_image_file(uri, fp, fmt)

        self.assertEqual(info.color_profile_bytes, None)

    def test_gray_jp2_info_from_image(self):
        fp = self.test_jp2_gray_fp
        fmt = self.test_jp2_gray_fmt
        ident = self.test_jp2_gray_id
        uri = self.test_jp2_gray_uri

        profile = ["http://iiif.io/api/image/2/level2.json", { 
            "formats": [ "jpg", "png", "gif" ],
            "qualities": [ 
                "default", 
                "bitonal", 
                "gray"
            ],
            "supports": [ 
                "canonical_link_header", 
                "mirroring",
                "rotation_arbitrary",
                "size_above_full" ]
            }
        ]
        formats = ["jpg", "png", "gif"]
        info = img_info.ImageInfo.from_image_file(uri, fp, fmt, formats)

        self.assertEqual(info.width, self.test_jp2_gray_dims[0])
        self.assertEqual(info.height, self.test_jp2_gray_dims[1])
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.tiles, self.test_jp2_gray_tiles)
        self.assertEqual(info.sizes, self.test_jp2_gray_sizes)
        self.assertEqual(info.ident, uri)
        self.assertEqual(info.protocol, PROTOCOL)

    def test_jpeg_info_from_image(self):
        fp = self.test_jpeg_fp
        fmt = self.test_jpeg_fmt
        ident = self.test_jpeg_id
        uri = self.test_jpeg_uri

        formats = ["jpg", "png", "gif"]
        info = img_info.ImageInfo.from_image_file(uri, fp, fmt, formats)

        profile = ["http://iiif.io/api/image/2/level2.json", { 
                "formats": [ "jpg", "png", "gif" ],
                "qualities": [ "default", "color", "gray", "bitonal" ],
                "supports": [ 
                    "canonical_link_header", 
                    "mirroring",
                    "rotation_arbitrary",
                    "size_above_full" 
                ]
            }
        ]

        self.assertEqual(info.width, self.test_jpeg_dims[0])
        self.assertEqual(info.height, self.test_jpeg_dims[1])
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.sizes, self.test_jpeg_sizes)
        self.assertEqual(info.ident, uri)
        self.assertEqual(info.protocol, PROTOCOL)

    def test_tiff_info_from_image(self):
        fp = self.test_tiff_fp
        fmt = self.test_tiff_fmt
        ident = self.test_tiff_id
        uri = self.test_tiff_uri

        formats = ["jpg", "png", "gif"]
        info = img_info.ImageInfo.from_image_file(uri, fp, fmt, formats)

        profile = ["http://iiif.io/api/image/2/level2.json", { 
                "formats": [ "jpg", "png", "gif" ],
                "qualities": [ "default", "color", "gray", "bitonal" ],
                "supports": [ 
                    "canonical_link_header", 
                    "mirroring", 
                    "rotation_arbitrary",
                    "size_above_full" 
                ]
            }
        ]

        self.assertEqual(info.width, self.test_tiff_dims[0])
        self.assertEqual(info.height, self.test_tiff_dims[1])
        self.assertEqual(info.sizes, self.test_tiff_sizes)
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.ident, uri)
        self.assertEqual(info.protocol, PROTOCOL)

    def test_info_from_json(self):
        json_fp = self.test_jp2_color_info_fp
        
        info = img_info.ImageInfo.from_json(json_fp)

        profile = ["http://iiif.io/api/image/2/level2.json", { 
                "formats": [ "jpg", "png", "gif" ],
                "qualities": [ "default", "bitonal", "gray", "color" ],
                "supports": [ 
                    "canonical_link_header", 
                    "mirroring", 
                    "rotation_arbitrary",
                    "size_above_full" 
                ]
            }
        ]

        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)
        self.assertEqual(info.ident, self.test_jp2_color_uri)
        self.assertEqual(info.sizes, self.test_jp2_color_sizes)
        self.assertEqual(info.protocol, PROTOCOL)


class Test_C_InfoFunctional(loris_t.LorisTest):
    'Simulate working with the API over HTTP.'

    def test_jp2_info_dot_json_request(self):
        resp = self.client.get('/%s/%s' % (self.test_jp2_color_id,'info.json'))
        self.assertEqual(resp.status_code, 200)

        tmp_fp = path.join(self.app.app_configs['loris.Loris']['tmp_dp'], 'loris_test_info.json')
        with open(tmp_fp, 'wb') as f:
            f.write(resp.data)

        profile = ["http://iiif.io/api/image/2/level2.json", { 
                "formats": [ "jpg", "png", "gif" ],
                "qualities": [ "default", "bitonal", "gray", "color" ],
                "supports": [ 
                    "canonical_link_header",
                    "mirroring",
                    "rotation_arbitrary",
                    "size_above_full"
                ]
            }
        ]

        info = img_info.ImageInfo.from_json(tmp_fp)
        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile, profile)
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)
        self.assertEqual(info.ident, self.test_jp2_color_uri)

    def test_json_ld_headers(self):
        'We should get jsonld if we ask for it'
        request_uri = '/%s/%s' % (self.test_jp2_color_id,'info.json')
        headers = Headers([('accept', 'application/ld+json')])
        resp = self.client.get(request_uri, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'application/ld+json')

    def test_json_by_default(self):
        'We should get json by default'
        request_uri = '/%s/%s' % (self.test_jp2_color_id,'info.json')
        resp = self.client.get(request_uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'application/json')

    def test_json_includes_a_link_to_the_context(self):
        'The Link header should include a link to the context'
        request_uri = '/%s/%s' % (self.test_jp2_color_id,'info.json')
        resp = self.client.get(request_uri)
        self.assertEqual(resp.status_code, 200)
        link_header = resp.headers['link']
        lh = '''
        <http://iiif.io/api/image/2/context.json>;
            rel="http://www.w3.org/ns/json-ld#context";
            type="application/ld+json"
        '''
        self.assertTrue(''.join(lh.split()) in link_header)

class Test_D_InfoCache(loris_t.LorisTest):
    pass
#
#   def test_info_cache(self):
#       pass

def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_B_InfoUnit, 'test'))
    test_suites.append(unittest.makeSuite(Test_C_InfoFunctional, 'test'))
    test_suites.append(unittest.makeSuite(Test_D_InfoCache, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
