
from loris.authorizer import _AbstractAuthorizer, NullAuthorizer,\
	NooneAuthorizer, SingleDegradingAuthorizer, RulesAuthorizer
from loris.img_info import ImageInfo

import unittest

class MockRequest(object):

	def __init__(self, hdrs={}, cooks={}):
		self.headers = hdrs
		self.cookies = cooks

class Test_AbstractAuthorizer(unittest.TestCase):
	
	def test_strip_empty_fields(self):
		aa = _AbstractAuthorizer({})
		self.assertEqual(aa._strip_empty_fields({"a": "", "b": 0, "c": False}), {})


# This is mostly pointless, as the values returned are static
class Test_NullAuthorizer(unittest.TestCase):

	def setUp(self):
		ident = "test"
		fp = "img/test.png"
		fmt = "png"
		self.authorizer = NullAuthorizer({})
		self.info = ImageInfo(ident, fp, fmt)
		self.request = MockRequest()

	def test_is_protected(self):
		self.assertEqual(self.authorizer.is_protected(self.info), False)

	def test_is_authorized(self):
		authd = self.authorizer.is_authorized(self.info, self.request)
		self.assertEqual(authd, {"status": "ok"})

	def test_get_services_info(self):
		svcs = self.authorizer.get_services_info(self.info)
		self.assertEqual(svcs, {})		


# This is also mostly pointless, as the values returned are static
class Test_NooneAuthorizer(unittest.TestCase):

	def setUp(self):
		ident = "test"
		fp = "img/test.png"
		fmt = "png"
		self.authorizer = NooneAuthorizer({})
		self.info = ImageInfo(ident, fp, fmt)
		self.request = MockRequest()

	def test_is_protected(self):
		self.assertEqual(self.authorizer.is_protected(self.info), True)

	def test_is_authorized(self):
		authd = self.authorizer.is_authorized(self.info, self.request)
		self.assertEqual(authd, {"status": "deny"})

	def test_get_services_info(self):
		svcs = self.authorizer.get_services_info(self.info)
		self.assertEqual(svcs['service']['profile'], "http://iiif.io/api/auth/1/login")

# This is ever-so-slightly less pointless
class Test_SingleDegradingAuthorizer(unittest.TestCase):

	def setUp(self):
		ident = "test"
		fp = "img/test.png"
		fmt = "png"
		self.authorizer = SingleDegradingAuthorizer({})
		self.badInfo = ImageInfo(ident, fp, fmt)
		self.okayInfo = ImageInfo("67352ccc-d1b0-11e1-89ae-279075081939.jp2",\
			"img/67352ccc-d1b0-11e1-89ae-279075081939.jp2", "jp2")
		self.request = MockRequest()

	def test_is_protected(self):
		self.assertEqual(self.authorizer.is_protected(self.badInfo), True)
		self.assertEqual(self.authorizer.is_protected(self.okayInfo), False)

	def test_is_authorized(self):
		authd = self.authorizer.is_authorized(self.badInfo, self.request)
		self.assertEqual(authd['status'], "redirect")

	def test_get_services_info(self):
		svcs = self.authorizer.get_services_info(self.badInfo)
		self.assertEqual(svcs['service']['profile'], "http://iiif.io/api/auth/1/login")
		svcs = self.authorizer.get_services_info(self.okayInfo)
		self.assertEqual(svcs['service']['profile'], "http://iiif.io/api/auth/1/login")

# And this is actually useful
class Test_RulesAuthorizer(unittest.TestCase):

	def setUp(self):
		ident = "test"
		fp = "img/test.png"
		fmt = "png"

		self.authorizer = RulesAuthorizer(
			{"cookie_secret": "4rakTQJDyhaYgoew802q78pNnsXR7ClvbYtAF1YC87o=",
			"token_secret": "hyQijpEEe9z1OB9NOkHvmSA4lC1B4lu1n80bKNx0Uz0="})
		self.badInfo = ImageInfo(ident, fp, fmt)		
		self.okayInfo = ImageInfo("67352ccc-d1b0-11e1-89ae-279075081939.jp2",\
			"img/67352ccc-d1b0-11e1-89ae-279075081939.jp2", "jp2")

		# role to get access is "test"
		# en/decryption defaults to return the plain text
		self.emptyRequest = MockRequest()

		cv = self.authorizer.cookie_fernet.encrypt("localhost|test")
		tv = self.authorizer.token_fernet.encrypt("localhost|test")

		self.tokenRequest = MockRequest(hdrs={"Authorization": "Bearer %s" % tv, "Origin": "localhost"})
		self.cookieRequest = MockRequest(hdrs={"Origin": "localhost"}, cooks={'iiif_access_cookie': cv})

	def test_basic_origin(self):

		tests = {"http://www.foobar.com/": "foobar.com",
			"https://www.foobar.com": "foobar.com",
			"http://foobar.com/": "foobar.com",
			"http://foobar.com/baz": "foobar.com",
			"http://foobar.co.uk/": "foobar.co.uk",
			"http://www.foobar.co.uk": "foobar.co.uk",
			"http://www.foobar.co.uk/baz": "foobar.co.uk",
			"http://foobar.com:80/": "foobar.com",
			"http://localhost:5004/": "localhost"
			}

		for (test, expect) in tests.items():
			self.assertEqual(self.authorizer.basic_origin(test), expect)

	def test_is_protected(self):
		self.badInfo.auth_rules = {"allowed": ["test"]}
		self.assertEqual(self.authorizer.is_protected(self.badInfo), True)
		self.assertEqual(self.authorizer.is_protected(self.okayInfo), False)

	def test_is_authorized(self):

		# No auth rules should pass for all
		authd = self.authorizer.is_authorized(self.okayInfo, self.emptyRequest)	
		self.assertEqual(authd['status'], "ok")
		authd = self.authorizer.is_authorized(self.okayInfo, self.tokenRequest)			
		self.assertEqual(authd['status'], "ok")
		authd = self.authorizer.is_authorized(self.okayInfo, self.cookieRequest)			
		self.assertEqual(authd['status'], "ok")

		# Set allowed role of "test"
		# Should fail for empty, pass for cookie/token
		self.badInfo.auth_rules = {"allowed": ["test"]}
		authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
		self.assertEqual(authd['status'], "deny")
		authd = self.authorizer.is_authorized(self.badInfo, self.tokenRequest)
		self.assertEqual(authd['status'], "ok")
		authd = self.authorizer.is_authorized(self.badInfo, self.cookieRequest)		
		self.assertEqual(authd['status'], "ok")

		# Set a degraded tier
		# Should redirect for empty, pass for cookie/token
		self.badInfo.auth_rules = {"allowed": ["test"], "tiers": 
			[{"identifier":"http://localhost:5004/"+self.okayInfo.ident}]}
		authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
		self.assertEqual(authd['status'], "redirect")
		authd = self.authorizer.is_authorized(self.badInfo, self.tokenRequest)		
		self.assertEqual(authd['status'], "ok")
		authd = self.authorizer.is_authorized(self.badInfo, self.cookieRequest)		
		self.assertEqual(authd['status'], "ok")

	def test_get_services_info(self):

		self.authorizer.cookie_service = "http://localhost:8000/cookie"

		self.badInfo.auth_rules = {"allowed":["test"],"extraInfo": {
			"service": {
				"@context": "http://iiif.io/api/auth/1/context.json", 
				"@id": "http://localhost:8000/cookie",
				"profile": "http://iiif.io/api/auth/1/login"}
			}}
		svcs = self.authorizer.get_services_info(self.badInfo)
		self.assertEqual(svcs['service']['profile'], "http://iiif.io/api/auth/1/login")


def suite():
	import unittest
	test_suites = []
	test_suites.append(unittest.makeSuite(Test_AbstractAuthorizer, 'test'))
	test_suites.append(unittest.makeSuite(Test_NullAuthorizer, 'test'))
	test_suites.append(unittest.makeSuite(Test_NooneAuthorizer, 'test'))
	test_suites.append(unittest.makeSuite(Test_SingleDegradingAuthorizer, 'test'))
	test_suites.append(unittest.makeSuite(Test_RulesAuthorizer, 'test'))
	test_suite = unittest.TestSuite(test_suites)
	return test_suite
