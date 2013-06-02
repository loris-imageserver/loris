#!/usr/bin/env python
# test.py
from tests import img_info_t
from tests import resolver_t
from tests import webapp_t
import unittest

test_suite = unittest.TestSuite()

test_suite.addTest(img_info_t.suite())
test_suite.addTest(resolver_t.suite())
test_suite.addTest(webapp_t.suite())

unittest.TextTestRunner(verbosity=3).run(test_suite)