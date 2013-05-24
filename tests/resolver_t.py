#-*- coding: utf-8 -*-

import loris_t
from os import path


"""
Resolver tests. This may need to be modified if you change the resolver 
implementation. To run this test on its own, do:

$ python -m unittest tests.resolver_t

from the `/loris` (not `/loris/loris`) directory.
"""

class A_ResolverTests(loris_t.LorisTest):
	'Test that the ID resolver works'

	def test_configured_resolver(self):
		expected_path = self.test_jp2_color_fp
		resolved_path, fmt = self.app.resolver.resolve(self.test_jp2_color_id)
		self.assertEqual(expected_path, resolved_path)
		self.assertEqual(fmt, 'jp2')
		self.assertTrue(path.isfile(resolved_path))

def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(A_ResolverTests, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite