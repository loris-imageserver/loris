#-*- coding: utf-8 -*-

from __future__ import absolute_import

from os.path import exists
from os.path import islink
from os.path import isfile
from os.path import join
import unittest

import mock
import pytest

try:
    from urllib.parse import unquote
except ImportError:  # Python 2
    from urllib import unquote

from loris import img, img_info
from loris.loris_exception import ImageException
from tests import loris_t


"""
Image and ImageCache tests. This may need to be modified if you change the resolver
implementation. To run this test on its own, do:

$ python -m unittest tests.img_t

from the `/loris` (not `/loris/loris`) directory.
"""

class TestImageRequest(object):

    def test_missing_info_attribute_is_error(self):
        request = img.ImageRequest('id1', 'full', 'full', '0', 'default', 'jpg')
        with pytest.raises(ImageException):
            request.info

    @pytest.mark.parametrize('args, request_path', [
        (('id1', 'full', 'full', '0', 'default', 'jpg'),
         'id1/full/full/0/default.jpg'),
        (('id2', '100,100,200,200', '200,', '30', 'gray', 'png'),
         'id2/100,100,200,200/200,/30/gray.png'),
    ])
    def test_request_path(self, args, request_path):
        request = img.ImageRequest(*args)
        assert request.request_path == request_path
        assert request.request_path == request_path


class Test_ImageCache(loris_t.LorisTest):

    def test_cache_entry_added(self):

        ident = self.test_jp2_color_id
        request_path = '/%s/full/pct:10/0/default.jpg' % (ident,)
        self.client.get(request_path)

        # the canonical path
        rel_cache_path = '%s/full/590,/0/default.jpg' % (unquote(ident),)
        expect_cache_path = join(self.app.img_cache.cache_root, rel_cache_path)

        self.assertTrue(exists(expect_cache_path))

    def test_symlink_added(self):
        ident = self.test_jp2_color_id
        params = 'full/pct:10/0/default.jpg'
        request_path = '/%s/%s' % (ident, params)

        self.client.get(request_path)

        # the symlink path
        rel_cache_path = '%s/%s' % (unquote(ident), params)
        expect_symlink = join(self.app.img_cache.cache_root, rel_cache_path)

        self.assertTrue(islink(expect_symlink))

    def test_canonical_requests_cache_at_canonical_path(self):
        ident = self.test_jp2_color_id
        # This is a canonical style request
        request_path = '%s/full/202,/0/default.jpg' % (ident,)
        self.client.get('/%s' % (request_path,))

        rel_cache_path = '%s/full/202,/0/default.jpg' % (unquote(ident),)
        expect_cache_path = join(self.app.img_cache.cache_root, rel_cache_path)

        self.assertTrue(exists(expect_cache_path))
        self.assertFalse(islink(expect_cache_path))

    def test_cache_dir_already_exists(self):
        ident = 'id1'
        image_info = img_info.ImageInfo(None)
        image_info.width = 100
        image_info.height = 100
        image_request = img.ImageRequest(ident, 'full', 'full', '0', 'default', 'jpg')
        image_request.info = image_info
        self.app.img_cache.create_dir_and_return_file_path(image_request)
        #call request again, so cache directory should already be there
        # throws an exception if we don't handle that existence properly
        self.app.img_cache.create_dir_and_return_file_path(image_request)

    def test_missing_entry_is_keyerror(self):
        cache = img.ImageCache(cache_root='/tmp')
        request = img.ImageRequest('id1', 'full', 'full', '0', 'default', 'jpg')

        with self.assertRaises(KeyError):
            cache[request]

    def test_missing_entry_gets_none(self):
        cache = img.ImageCache(cache_root='/tmp')
        request = img.ImageRequest('id1', 'full', 'full', '0', 'default', 'jpg')

        self.assertIsNone(cache.get(request))

    def test_getitem_with_unexpected_error_is_raised(self):
        cache = img.ImageCache(cache_root='/tmp')
        request = img.ImageRequest('id', 'full', 'full', '0', 'default', 'jpg')

        message = "Exception thrown in img_t.py for Test_ImageCache"
        m = mock.Mock(side_effect=OSError(-1, message))
        with mock.patch('loris.img.path.getmtime', m):
            with pytest.raises(OSError) as err:
                cache[request]


def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_ImageCache, 'test'))
    test_suites.append(unittest.makeSuite(TestImageRequest, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
