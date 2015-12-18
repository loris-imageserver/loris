#-*- coding: utf-8 -*-

from os.path import exists
from os.path import islink
from os.path import isfile
from os.path import join
from urllib import unquote
from loris.webapp import Loris
import loris_t


"""
Image and ImageCache tests. This may need to be modified if you change the resolver
implementation. To run this test on its own, do:

$ python -m unittest tests.img_t

from the `/loris` (not `/loris/loris`) directory.
"""

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


class Test_NoInterpolation(loris_t.LorisTest):

    def setUp(self):
        super(Test_NoInterpolation, self).setUp()
        self.app.size_above_full = False
        self.app.max_size_above_full = 200


    def test_width(self):
        self.assertFalse(Loris._size_exeeds_original('200,', 200, 100, 100))
        self.assertTrue(Loris._size_exeeds_original('300,', 200, 100, 100))

    def test_height(self):
        self.assertFalse(Loris._size_exeeds_original(',100', 200, 100, 100))
        self.assertTrue(Loris._size_exeeds_original(',200', 200, 100, 100))

    def test_percentage(self):
        self.assertFalse(Loris._size_exeeds_original('pct:50', 200, 100, 100))
        self.assertFalse(Loris._size_exeeds_original('pct:100', 200, 100, 100))
        self.assertTrue(Loris._size_exeeds_original('pct:101', 200, 100, 100))

    def test_force_aspect(self):
        self.assertFalse(Loris._size_exeeds_original('!50,150', 200, 100, 100))
        self.assertFalse(Loris._size_exeeds_original('!20,50', 200, 100, 100))
        self.assertFalse(Loris._size_exeeds_original('!200,100', 200, 100, 100))
        self.assertTrue(Loris._size_exeeds_original('!250,150', 200, 100, 100))


class Test_RestrictedInterpolation(loris_t.LorisTest):

    def setUp(self):
        super(Test_RestrictedInterpolation, self).setUp()
        self.app.size_above_full = True
        self.app.max_size_above_full = 200

    def test_interpolation_limit(self):
        self.assertFalse(Loris._size_exeeds_original('300,', 200, 100, 200))
        self.assertTrue(Loris._size_exeeds_original('500,', 200, 100, 200))

    def test_percentage(self):
        self.assertFalse(Loris._size_exeeds_original('pct:50', 200, 100, 200))
        self.assertFalse(Loris._size_exeeds_original('pct:200', 200, 100, 200))
        self.assertTrue(Loris._size_exeeds_original('pct:201', 200, 100, 200))


def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_ImageCache, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
