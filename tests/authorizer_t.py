from loris.authorizer import _AbstractAuthorizer, NullAuthorizer,\
    NooneAuthorizer, SingleDegradingAuthorizer, RulesAuthorizer
from loris.loris_exception import ConfigError
from loris.img_info import ImageInfo

import unittest
import base64
from cryptography.fernet import Fernet
import jwt
import pytest


class MockRequest:

    def __init__(self, hdrs={}, cooks={}):
        self.headers = hdrs
        self.cookies = cooks
        self.path = "bla/info.json"


class Test_AbstractAuthorizer(unittest.TestCase):

    def test_strip_empty_fields(self):
        aa = _AbstractAuthorizer({})
        d = {"a": "", "b": 0, "c": False}
        aa._strip_empty_fields(d)
        self.assertEqual(d, {})

    def test_is_protected_is_notimplementederror(self):
        aa = _AbstractAuthorizer({})
        with pytest.raises(NotImplementedError):
            aa.is_protected(info={})

    def test_get_services_info_is_notimplementederror(self):
        aa = _AbstractAuthorizer({})
        with pytest.raises(NotImplementedError):
            aa.get_services_info(info={})

    def test_is_authorized_is_notimplementederror(self):
        aa = _AbstractAuthorizer({})
        with pytest.raises(NotImplementedError):
            aa.is_authorized(info={}, request=None)


class Test_NullAuthorizer(unittest.TestCase):

    def setUp(self):
        ident = "test"
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = NullAuthorizer({})
        self.info = ImageInfo(None, fp, fmt)
        self.request = MockRequest()

    def test_is_protected(self):
        self.assertEqual(self.authorizer.is_protected(self.info), False)

    def test_is_authorized(self):
        authd = self.authorizer.is_authorized(self.info, self.request)
        self.assertEqual(authd, {"status": "ok"})

    def test_get_services_info(self):
        svcs = self.authorizer.get_services_info(self.info)
        self.assertEqual(svcs, {})


class Test_NooneAuthorizer(unittest.TestCase):

    def setUp(self):
        ident = "test"
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = NooneAuthorizer({})
        self.info = ImageInfo(None, fp, fmt)
        self.request = MockRequest()

    def test_is_protected(self):
        self.assertEqual(self.authorizer.is_protected(self.info), True)

    def test_is_authorized(self):
        authd = self.authorizer.is_authorized(self.info, self.request)
        self.assertEqual(authd, {"status": "deny"})

    def test_get_services_info(self):
        svcs = self.authorizer.get_services_info(self.info)
        self.assertEqual(svcs['service']['profile'], "http://iiif.io/api/auth/1/login")


class Test_SingleDegradingAuthorizer(unittest.TestCase):

    def setUp(self):
        ident = "test"
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = SingleDegradingAuthorizer({})
        self.badInfo = ImageInfo(None, fp, fmt)
        self.okayIdent = "67352ccc-d1b0-11e1-89ae-279075081939.jp2"
        self.okayInfo = ImageInfo(None, "img/%s" % self.okayIdent, "jp2")
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


class Test_RulesAuthorizer(unittest.TestCase):

    def setUp(self):
        ident = "test"
        fp = "img/test.png"
        fmt = "png"

        self.authorizer = RulesAuthorizer(
            {"cookie_secret": b"4rakTQJDyhaYgoew802q78pNnsXR7ClvbYtAF1YC87o=",
            "token_secret": b"hyQijpEEe9z1OB9NOkHvmSA4lC1B4lu1n80bKNx0Uz0=",
            "salt": b"4rakTQJD4lC1B4lu"})
        self.badInfo = ImageInfo(None, fp, fmt)
        self.okayIdent = "67352ccc-d1b0-11e1-89ae-279075081939.jp2"
        self.okayInfo = ImageInfo(None, "img/%s" % self.okayIdent, "jp2")

        self.origin = "localhost"
        # role to get access is "test"
        # en/decryption defaults to return the plain text
        self.emptyRequest = MockRequest()

        secret = b'-'.join([self.authorizer.token_secret, self.origin.encode('utf8')])
        key = base64.urlsafe_b64encode(self.authorizer.kdf().derive(secret))
        self.token_fernet = Fernet(key)
        tv = self.token_fernet.encrypt(b"localhost|test")
        jwt_tv = jwt.encode({u"sub": u"test"}, secret, algorithm='HS256')
        jwt_tv_roles = jwt.encode({u"roles": [u'test']}, secret, algorithm='HS256')

        secret = b'-'.join([self.authorizer.cookie_secret, self.origin.encode('utf8')])
        key = base64.urlsafe_b64encode(self.authorizer.kdf().derive(secret))
        self.cookie_fernet = Fernet(key)
        cv = self.cookie_fernet.encrypt(b"localhost|test")
        jwt_cv = jwt.encode({"sub": "test"}, secret, algorithm='HS256')
        jwt_cv_roles = jwt.encode({"roles": ['test']}, secret, algorithm='HS256')

        self.tokenRequest = MockRequest(hdrs={"Authorization": b"Bearer " + tv, "origin": self.origin})
        self.cookieRequest = MockRequest(hdrs={"origin": self.origin}, cooks={'iiif_access_cookie': cv})
        self.cookieRequest.path = ".../default.jpg"

        self.jwtTokenRequest = MockRequest(hdrs={"Authorization": b"Bearer " + jwt_tv, "origin": self.origin})
        self.jwtCookieRequest = MockRequest(hdrs={"origin": self.origin}, cooks={'iiif_access_cookie': jwt_cv})
        self.jwtCookieRequest.path = ".../default.jpg"


    def test_basic_origin(self):

        tests = {"http://www.foobar.com/": "foobar.com",
            "https://www.foobar.com": "foobar.com",
            "http://foobar.com/": "foobar.com",
            "http://foobar.com/baz": "foobar.com",
            "http://foobar.co.uk/": "foobar.co.uk",
            "http://www.foobar.co.uk": "foobar.co.uk",
            "http://www.foobar.co.uk/baz": "foobar.co.uk",
            "http://foobar.com:80/": "foobar.com",
            "http://localhost:5004/": "localhost",
            "http://10.0.0.1/": "10.0.0.1",
            "https://x.y.z.foo.com": "foo.com",
            "http://x.y.z.foo.co.uk": "foo.co.uk",
            "www.foobar.com": "foobar.com",
            "localhost.localdomain": "localhost.localdomain",
            "x.y.z.foo.co.uk": "foo.co.uk"
            }

        for (test, expect) in tests.items():
            self.assertEqual(self.authorizer.basic_origin(test), expect)

    def test_is_protected(self):
        self.badInfo.auth_rules = {"allowed": ["test"]}
        self.assertEqual(self.authorizer.is_protected(self.badInfo), True)
        self.assertEqual(self.authorizer.is_protected(self.okayInfo), False)

    def test_is_authorized(self):

        # Set use_jwt to False
        self.authorizer.use_jwt = False

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

        # Set allowed role of "!test"
        # Should fail for all, as test != !test
        self.badInfo.auth_rules = {"allowed": ["!test"]}
        authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "deny")
        authd = self.authorizer.is_authorized(self.badInfo, self.tokenRequest)
        self.assertEqual(authd['status'], "deny")
        authd = self.authorizer.is_authorized(self.badInfo, self.cookieRequest)
        self.assertEqual(authd['status'], "deny")


        # Set a degraded tier
        # Should redirect for empty, pass for cookie/token
        self.badInfo.auth_rules = {"allowed": ["test"], "tiers":
            [{"identifier":"http://localhost:5004/"+self.okayIdent}]}
        authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "redirect")
        authd = self.authorizer.is_authorized(self.badInfo, self.tokenRequest)
        self.assertEqual(authd['status'], "ok")
        authd = self.authorizer.is_authorized(self.badInfo, self.cookieRequest)
        self.assertEqual(authd['status'], "ok")

    def test_is_authorized_jwt(self):

        # Set use_jwt to True
        self.authorizer.use_jwt = True

        # No auth rules should still pass for all
        authd = self.authorizer.is_authorized(self.okayInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "ok")
        authd = self.authorizer.is_authorized(self.okayInfo, self.jwtTokenRequest)
        self.assertEqual(authd['status'], "ok")
        authd = self.authorizer.is_authorized(self.okayInfo, self.jwtCookieRequest)
        self.assertEqual(authd['status'], "ok")

        # Set allowed role of "test"
        # Should fail for empty, pass for cookie/token
        self.badInfo.auth_rules = {"allowed": ["test"]}
        authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "deny")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtTokenRequest)
        self.assertEqual(authd['status'], "ok")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtCookieRequest)
        self.assertEqual(authd['status'], "ok")

        # Set allowed role of "!test"
        # Should fail for all, as test != !test
        self.badInfo.auth_rules = {"allowed": ["!test"]}
        authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "deny")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtTokenRequest)
        self.assertEqual(authd['status'], "deny")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtCookieRequest)
        self.assertEqual(authd['status'], "deny")

        # Set a degraded tier
        # Should redirect for empty, pass for cookie/token
        self.badInfo.auth_rules = {"allowed": ["test"], "tiers":
            [{"identifier":"http://localhost:5004/"+self.okayIdent}]}
        authd = self.authorizer.is_authorized(self.badInfo, self.emptyRequest)
        self.assertEqual(authd['status'], "redirect")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtTokenRequest)
        self.assertEqual(authd['status'], "ok")
        authd = self.authorizer.is_authorized(self.badInfo, self.jwtCookieRequest)
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

    def test_missing_cookie_secret_is_configerror(self):
        config = {
            'cookie_service': 'cookie.example.com',
            'token_service': 'token.example.com',
            'token_secret': 't0k3ns3kr1t'
        }
        with pytest.raises(ConfigError) as err:
            RulesAuthorizer(config)
        assert (
            'Missing mandatory parameters for RulesAuthorizer: cookie_secret' ==
            str(err.value)
        )

    def test_missing_token_secret_is_configerror(self):
        config = {
            'cookie_service': 'cookie.example.com',
            'token_service': 'token.example.com',
            'cookie_secret': 'c00ki3sekr1t',
        }
        with pytest.raises(ConfigError) as err:
            RulesAuthorizer(config)
        assert (
            'Missing mandatory parameters for RulesAuthorizer: token_secret' ==
            str(err.value)
        )

    def test_false_use_jwt_without_salt_is_configerror(self):
        config = {
            'cookie_service': 'cookie.example.com',
            'token_service': 'token.example.com',
            'cookie_secret': 'c00ki3sekr1t',
            'token_secret': 't0k3ns3kr1t',
            'use_jwt': False,
        }
        with pytest.raises(ConfigError) as err:
            RulesAuthorizer(config)
        assert (
            'If use_jwt=False, you must supply the "salt" config parameter' ==
            str(err.value)
        )

    def test_salt_must_be_bytes(self):
        config = {
            'cookie_service': 'cookie.example.com',
            'token_service': 'token.example.com',
            'cookie_secret': 'c00ki3sekr1t',
            'token_secret': 't0k3ns3kr1t',
            'use_jwt': False,
            'salt': u'salt',
        }
        with pytest.raises(ConfigError) as err:
            RulesAuthorizer(config)
        assert (
            str(err.value).startswith('"salt" config parameter must be bytes;')
        )

