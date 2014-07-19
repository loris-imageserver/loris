#-*- coding: utf-8 -*-

from loris.resolver import SourceImageCachingResolver
from os.path import dirname
from os.path import isfile
from os.path import join
from os.path import realpath
from urllib import unquote
import loris_t


"""
Resolver tests. This may need to be modified if you change the resolver 
implementation. To run this test on its own, do:

$ python -m unittest tests.resolver_t

from the `/loris` (not `/loris/loris`) directory.
"""

class Test_SimpleFSResolver(loris_t.LorisTest):
	'Test that the default resolver works'

	def test_configured_resolver(self):
		expected_path = self.test_jp2_color_fp
		resolved_path, fmt = self.app.resolver.resolve(self.test_jp2_color_id)
		self.assertEqual(expected_path, resolved_path)
		self.assertEqual(fmt, 'jp2')
		self.assertTrue(isfile(resolved_path))

class Test_SourceImageCachingResolver(loris_t.LorisTest):
	'Test that the SourceImageCachingResolver resolver works'

	def test_source_image_caching_resolver(self):
		# First we need to change the resolver on the test instance of the 
		# application (overrides the config to use SimpleFSResolver)
		config = {
			'source_root' : join(dirname(realpath(__file__)), 'img'), 
			'cache_root' : self.app.img_cache.cache_root
		}
		self.app.resolver = SourceImageCachingResolver(config)

		# Now...
		ident = self.test_jp2_color_id
		resolved_path, fmt = self.app.resolver.resolve(ident)
		expected_path = join(self.app.img_cache.cache_root, unquote(ident))

		self.assertEqual(expected_path, resolved_path)
		self.assertEqual(fmt, 'jp2')
		self.assertTrue(isfile(resolved_path))

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(Test_SimpleFSResolver, 'test'))
	test_suites.append(unittest.makeSuite(Test_SourceImageCachingResolver, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite
