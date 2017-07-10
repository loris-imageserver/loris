#!/usr/bin/env python
# test.py
from sys import exit
from tests import authorizer_t
from tests import img_info_t
from tests import parameters_t
from tests import resolver_t
from tests import webapp_t
from tests import transforms_t
from tests import img_t
from tests import simple_fs_resolver_ut
from tests import simple_http_resolver_ut
from tests import source_image_caching_resolver_ut
from unittest import TestSuite, TextTestRunner

test_suite = TestSuite()
test_suite.addTest(authorizer_t.suite())
test_suite.addTest(img_info_t.suite())
test_suite.addTest(transforms_t.suite())
test_suite.addTest(parameters_t.suite())
test_suite.addTest(resolver_t.suite())
test_suite.addTest(webapp_t.suite())
test_suite.addTest(img_t.suite())
test_suite.addTest(simple_fs_resolver_ut.suite())
test_suite.addTest(simple_http_resolver_ut.suite())
test_suite.addTest(source_image_caching_resolver_ut.suite())

runner = TextTestRunner(verbosity=3)
ret = not runner.run(test_suite).wasSuccessful()
exit(ret)
