#!/usr/bin/env python
# test.py
from tests import img_info_t
from tests import parameters_t
from tests import resolver_t
from tests import webapp_t
from tests import transforms_t
from tests import img_t
from unittest import TestSuite, TextTestRunner

test_suite = TestSuite()
test_suite.addTest(img_info_t.suite())
test_suite.addTest(transforms_t.suite())
test_suite.addTest(parameters_t.suite())
test_suite.addTest(resolver_t.suite())
test_suite.addTest(webapp_t.suite())
test_suite.addTest(img_t.suite())

TextTestRunner(verbosity=3).run(test_suite)
