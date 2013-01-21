# test.py
import test.suite
import unittest

suite = test.suite.all_tests()
unittest.TextTestRunner(verbosity=3).run(suite)