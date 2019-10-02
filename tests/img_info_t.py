import os
from os import path
import json
import tempfile
from datetime import datetime

import pytest
from werkzeug.datastructures import Headers

from loris import img_info, loris_exception
from loris.img_info import ImageInfo, Profile
from loris.loris_exception import ImageInfoException
from tests import loris_t


class MockApp:
    transformers = {}
    max_size_above_full = 200

    def __init__(self, formats=["jpg", "png", "gif", "webp"], msaf=200):
        self.transformers = {'jp2': formats, 'png': formats}
        self.max_size_above_full = msaf


class InfoUnit(loris_t.LorisTest):

    def test_color_jp2_info_from_image(self):
        fp = self.test_jp2_color_fp
        fmt = self.test_jp2_color_fmt
        ident = self.test_jp2_color_id
        uri = self.test_jp2_color_uri

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp", "tif" ],
                "qualities": [
                    "default",
                    "bitonal",
                    "gray",
                    "color"
                ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare"
                ]
            }
        ]

        #test that sizeAboveFull isn't in profile if max_size_above_full is > 0 and <= 100
        self.app.max_size_above_full = 80
        info = img_info.ImageInfo(self.app, fp, fmt)

        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)
        self.assertEqual(info.sizes, self.test_jp2_color_sizes)

        self.app.max_size_above_full = 0
        info = img_info.ImageInfo(self.app, fp, fmt)
        self.assertTrue('sizeAboveFull' in info.profile.description['supports'])
        self.app.max_size_above_full = 200


    def test_precinct_jp2_tiles_from_image(self):
        fp = self.test_jp2_with_precincts_fp
        fmt = self.test_jp2_with_precincts_fmt
        ident = self.test_jp2_with_precincts_id
        uri = self.test_jp2_with_precincts_uri

        info = img_info.ImageInfo(self.app, fp, fmt)

        self.assertEqual(info.tiles, self.test_jp2_with_precincts_tiles)
        self.assertEqual(info.sizes, self.test_jp2_with_precincts_sizes)

    def test_extract_icc_profile_from_jp2(self):
        fp = self.test_jp2_with_embedded_profile_fp
        fmt = self.test_jp2_with_embedded_profile_fmt
        ident = self.test_jp2_with_embedded_profile_id
        uri = self.test_jp2_with_embedded_profile_uri
        profile_copy_fp = self.test_jp2_embedded_profile_copy_fp

        info = img_info.ImageInfo(self.app, fp, fmt)

        with open(self.test_jp2_embedded_profile_copy_fp, 'rb') as fixture_bytes:
            self.assertEqual(info.color_profile_bytes, fixture_bytes.read())

    def test_no_embedded_profile_info_color_profile_bytes_is_None(self):
        fp = self.test_jp2_color_fp
        fmt = self.test_jp2_color_fmt
        ident = self.test_jp2_color_id
        uri = self.test_jp2_color_uri

        info = img_info.ImageInfo(self.app, fp, fmt)
        self.assertEqual(info.color_profile_bytes, None)

    def test_gray_jp2_info_from_image(self):
        fp = self.test_jp2_gray_fp
        fmt = self.test_jp2_gray_fmt
        ident = self.test_jp2_gray_id
        uri = self.test_jp2_gray_uri

        profile = ["http://iiif.io/api/image/2/level2.json", {
            "formats": [ "jpg", "png", "gif", "webp", "tif" ],
            "qualities": [
                "default",
                "bitonal",
                "gray"
            ],
            "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare",
                    "sizeAboveFull"
                ]
            }
        ]

        info = img_info.ImageInfo(self.app, fp, fmt)

        self.assertEqual(info.width, self.test_jp2_gray_dims[0])
        self.assertEqual(info.height, self.test_jp2_gray_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.tiles, self.test_jp2_gray_tiles)
        self.assertEqual(info.sizes, self.test_jp2_gray_sizes)

    def test_info_from_jpg_marked_as_jp2(self):
        fp = path.join(self.test_img_dir, '01', '03', '0001.jpg')
        fmt = 'jp2'
        ident = '01%2f03%2f0001.jpg'
        uri = '%s/%s' % (self.URI_BASE, ident)
        with self.assertRaises(loris_exception.ImageInfoException) as cm:
            img_info.ImageInfo(self.app, fp, fmt)
        self.assertEqual(str(cm.exception), 'Invalid JP2 file')

    def test_info_from_invalid_src_format(self):
        fp = path.join(self.test_img_dir, '01', '03', '0001.jpg')
        fmt = 'invalid_format'
        ident = '01%2f03%2f0001.jpg'
        uri = '%s/%s' % (self.URI_BASE, ident)
        error_message = "Didn\'t get a source format, or at least one we recognize ('invalid_format')."
        with self.assertRaises(loris_exception.ImageInfoException) as cm:
            img_info.ImageInfo(self.app, fp, fmt)
        self.assertEqual(str(cm.exception), error_message)

    def test_jpeg_info_from_image(self):
        fp = self.test_jpeg_fp
        fmt = self.test_jpeg_fmt
        ident = self.test_jpeg_id
        uri = self.test_jpeg_uri

        info = img_info.ImageInfo(self.app, fp, fmt)

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp", "tif" ],
                "qualities": [ "default", "color", "gray", "bitonal" ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare",
                    "sizeAboveFull"
                ]
            }
        ]

        self.assertEqual(info.width, self.test_jpeg_dims[0])
        self.assertEqual(info.height, self.test_jpeg_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.sizes, self.test_jpeg_sizes)

    def test_png_info_from_image(self):
        fp = self.test_png_fp
        fmt = self.test_png_fmt
        ident = self.test_png_id
        uri = self.test_png_uri

        info = img_info.ImageInfo(self.app, fp, fmt)

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp", "tif" ],
                "qualities": [ "default", "gray", "bitonal" ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare",
                    "sizeAboveFull"
                ]
            }
        ]

        self.assertEqual(info.width, self.test_png_dims[0])
        self.assertEqual(info.height, self.test_png_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.sizes, self.test_png_sizes)


    def test_tiff_info_from_image(self):
        fp = self.test_tiff_fp
        fmt = self.test_tiff_fmt
        ident = self.test_tiff_id
        uri = self.test_tiff_uri

        info = img_info.ImageInfo(self.app, fp, fmt)

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp", "tif" ],
                "qualities": [ "default", "color", "gray", "bitonal" ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare",
                    "sizeAboveFull"
                ]
            }
        ]

        self.assertEqual(info.width, self.test_tiff_dims[0])
        self.assertEqual(info.height, self.test_tiff_dims[1])
        self.assertEqual(info.sizes, self.test_tiff_sizes)
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])

    def test_info_from_json(self):
        json_fp = self.test_jp2_color_info_fp

        info = img_info.ImageInfo.from_json_fp(json_fp)

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp" ],
                "qualities": [ "default", "bitonal", "gray", "color" ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "sizeAboveFull",
                    "regionSquare"
                ]
            }
        ]

        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)
        self.assertEqual(info.sizes, self.test_jp2_color_sizes)

    def test_extrainfo_appears_in_iiif_json(self):
        info = ImageInfo(
            src_img_fp=self.test_jpeg_fp,
            src_format=self.test_jpeg_fmt,
            extra={'extraInfo': {
                'license': 'CC-BY',
                'logo': 'logo.png',
                'service': {'@id': 'my_service'},
                'attribution': 'Author unknown',
            }}
        )
        info.from_image_file()

        iiif_json = json.loads(info.to_iiif_json(base_uri='http://localhost/1234'))
        assert iiif_json['license'] == 'CC-BY'
        assert iiif_json['logo'] == 'logo.png'
        assert iiif_json['service'] == {'@id': 'my_service'}
        assert iiif_json['attribution'] == 'Author unknown'


class TestImageInfo:

    def test_extrainfo_can_override_attributes(self):
        info = ImageInfo(extra={'extraInfo': {
            'license': 'CC-BY',
            'logo': 'logo.png',
            'service': {'@id': 'my_service'},
            'attribution': 'Author unknown',
        }})
        assert info.license == 'CC-BY'
        assert info.logo == 'logo.png'
        assert info.service == {'@id': 'my_service'}
        assert info.attribution == 'Author unknown'

    def test_invalid_extra_info_is_imageinfoexception(self):
        with pytest.raises(ImageInfoException) as exc:
            ImageInfo(extra={'extraInfo': {'foo': 'bar', 'baz': 'bat'}})
        assert 'Invalid parameters in extraInfo' in str(exc.value)

    @pytest.mark.parametrize('src_format', ['', None, 'imgX'])
    def test_invalid_src_format_is_error(self, src_format):
        info = ImageInfo(src_format=src_format)
        with pytest.raises(ImageInfoException) as exc:
            info.from_image_file()

    def test_profile_from_json_no_profile(self):
        existing_info = {}
        info = ImageInfo.from_json(json.dumps(existing_info))

        assert info.profile.compliance_uri == ''
        assert info.profile.description == {}

    def test_profile_from_json_one_arg_profile(self):
        compliance_uri = 'http://iiif.io/api/image/2/level2.json'
        existing_info = {
            'profile': [compliance_uri]
        }
        info = ImageInfo.from_json(json.dumps(existing_info))

        assert info.profile.compliance_uri == compliance_uri
        assert info.profile.description == {}

    def test_profile_from_json_two_arg_profile(self):
        compliance_uri = 'http://iiif.io/api/image/2/level2.json'
        description = {
            'formats': ['jpg', 'png', 'gif', 'webp', 'tif'],
            'qualities': ['default', 'bitonal', 'gray', 'color'],
            'supports': [
                'canonicalLinkHeader',
                'profileLinkHeader',
                'mirroring',
                'rotationArbitrary',
                'sizeAboveFull',
                'regionSquare'
            ]
        }
        existing_info = {
            'profile': [compliance_uri, description]
        }
        info = ImageInfo.from_json(json.dumps(existing_info))

        assert info.profile.compliance_uri == compliance_uri
        assert info.profile.description == description


class TestProfile(object):

    compliance_uri = 'http://iiif.io/api/image/2/level2.json'
    description = {
        'formats': ['gif', 'pdf'],
        'qualities': ['color', 'gray'],
        'maxWidth': 2000,
        'supports': ['canonicalLinkHeader', 'rotationArbitrary']
    }

    def test_construct_no_args(self):
        p = Profile()
        assert p.compliance_uri == ''
        assert p.description == {}

    def test_construct_one_args(self):
        p = Profile(self.compliance_uri)
        assert p.compliance_uri == self.compliance_uri
        assert p.description == {}

    def test_construct_two_args(self):
        p = Profile(self.compliance_uri, self.description)
        assert p.compliance_uri == self.compliance_uri
        assert p.description == self.description

    def test_json_encoding_with_no_description(self):
        p = Profile(self.compliance_uri)
        json_string = json.dumps(
            {'profile': p}, cls=img_info.EnhancedJSONEncoder
        )
        assert json.loads(json_string)['profile'] == [self.compliance_uri]

    def test_json_encoding_with_description(self):
        p = Profile(self.compliance_uri, self.description)
        json_string = json.dumps(
            {'profile': p}, cls=img_info.EnhancedJSONEncoder
        )
        assert json.loads(json_string)['profile'] == [
            self.compliance_uri, self.description
        ]


class InfoFunctional(loris_t.LorisTest):
    'Simulate working with the API over HTTP.'

    def test_jp2_info_dot_json_request(self):
        resp = self.client.get('/%s/%s' % (self.test_jp2_color_id,'info.json'))
        self.assertEqual(resp.status_code, 200)

        tmp_fp = path.join(self.app.app_configs['loris.Loris']['tmp_dp'], 'loris_test_info.json')
        with open(tmp_fp, 'wb') as f:
            f.write(resp.data)

        profile = ["http://iiif.io/api/image/2/level2.json", {
                "formats": [ "jpg", "png", "gif", "webp", "tif" ],
                "qualities": [ "default", "bitonal", "gray", "color" ],
                "supports": [
                    "canonicalLinkHeader",
                    "profileLinkHeader",
                    "mirroring",
                    "rotationArbitrary",
                    "regionSquare",
                    "sizeAboveFull"
                ]
            }
        ]

        info = img_info.ImageInfo.from_json_fp(tmp_fp)
        self.assertEqual(info.width, self.test_jp2_color_dims[0])
        self.assertEqual(info.height, self.test_jp2_color_dims[1])
        self.assertEqual(info.profile.compliance_uri, profile[0])
        self.assertEqual(info.profile.description, profile[1])
        self.assertEqual(info.tiles, self.test_jp2_color_tiles)

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


class TestInfoCache(loris_t.LorisTest):

    def _cache_with_ident(self):
        """
        Returns a tuple: an ``InfoCache`` with a single entry, and the key.
        """
        cache = img_info.InfoCache(root=self.SRC_IMAGE_CACHE)

        info = img_info.ImageInfo(self.app, self.test_jp2_color_fp, self.test_jp2_color_fmt)

        cache[self.test_jp2_color_id] = info
        return (cache, self.test_jp2_color_id)

    def test_info_goes_to_expected_path(self):
        expected_path_for_id = '1b/372/221/d29/35d/2eb/82a/1f8/021/1ee/89f'
        request_uri = '/%s/%s' % (self.test_jp2_color_id, 'info.json')
        resp = self.client.get(request_uri)
        expected_path = path.join(
            self.app.info_cache.root,
            expected_path_for_id,
            'info.json'
        )
        self.assertTrue(path.exists(expected_path))

    def test_just_ram_cache_update(self):
        # Cache size of one, so it's easy to manipulate
        with tempfile.TemporaryDirectory() as cache_root:
            cache = img_info.InfoCache(root=cache_root, size=1)
            self.app.info_cache = cache
            expected_path_for_id = '1b/372/221/d29/35d/2eb/82a/1f8/021/1ee/89f'
            # First request
            request_uri = '/%s/%s' % (self.test_jp2_color_id,'info.json')
            resp = self.client.get(request_uri)
            expected_path = path.join(
                self.app.info_cache.root,
                expected_path_for_id,
                'info.json'
            )
            fs_first_time = datetime.utcfromtimestamp(os.path.getmtime(expected_path))
            # Push this entry out of the RAM cache with another
            push_request_uri = '/%s/%s' % (self.test_jp2_gray_id,'info.json')
            resp = self.client.get(push_request_uri)
            # Request the first file again
            # It should now exist on disk, but not in RAM, so it shouldn't
            # have been rewritten by the second get.
            resp = self.client.get(request_uri)
            fs_second_time = datetime.utcfromtimestamp(os.path.getmtime(expected_path))
            self.assertTrue(fs_first_time == fs_second_time)

    def test_can_delete_items_from_infocache(self):
        cache, ident = self._cache_with_ident()
        del cache[ident]

    def test_empty_cache_has_zero_size(self):
        cache = img_info.InfoCache(root=self.SRC_IMAGE_CACHE)
        assert len(cache) == 0

    def test_cache_limit(self):
        cache = img_info.InfoCache(root=self.SRC_IMAGE_CACHE, size=2)
        self.app.info_cache = cache
        request_uris = [
            '/%s/%s' % (self.test_jp2_color_id,'info.json'),
            '/%s/%s' % (self.test_jpeg_id,'info.json'),
            '/%s/%s' % (self.test_png_id,'info.json'),
            '/%s/%s' % (self.test_jp2_gray_id,'info.json')
        ]
        for x in request_uris:
            resp = self.client.get(x)

        # Check we only cache two
        assert len(self.app.info_cache) == 2

    def test_no_cache(self):
        cache = img_info.InfoCache(root=self.SRC_IMAGE_CACHE, size=0)
        self.app.info_cache = cache
        request_uri = '/%s/%s' % (self.test_jp2_color_id,'info.json')
        resp = self.client.get(request_uri)

        assert len(self.app.info_cache) == 0

    def test_deleting_cache_item_removes_color_profile_fp(self):
        # First assemble the cache
        cache, ident = self._cache_with_ident()

        # Then create a file where the cached color profile would be
        color_profile_fp = cache._get_color_profile_fp(ident)
        with open(color_profile_fp, 'w'): pass
        assert os.path.exists(color_profile_fp)

        # Finally, delete the cache entry, and check the color profile fp
        # was deleted.
        del cache[ident]
        assert not os.path.exists(color_profile_fp)

    def test_looking_up_missing_item_is_keyerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = img_info.InfoCache(root=tmp)
            with pytest.raises(KeyError):
                cache[self.test_jp2_color_id]

    def test_creates_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "doesnotexist")
            assert not os.path.exists(root)
            cache = img_info.InfoCache(root=root)

            info = img_info.ImageInfo(
                app=self.app,
                src_img_fp=self.test_jpeg_fp,
                src_format=self.test_jpeg_fmt
            )

            cache[self.test_jpeg_id] = info
            assert cache[self.test_jpeg_id][0] == info
