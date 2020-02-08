import base64
import collections
import datetime
import unittest

from cryptography.fernet import Fernet
import jwt
import pytest

from loris.authorizer import _AbstractAuthorizer, NullAuthorizer,\
    NooneAuthorizer, SingleDegradingAuthorizer, RulesAuthorizer
from loris.loris_exception import ConfigError
from loris.img_info import ImageInfo


class MockRequest:

    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}
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
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = NullAuthorizer({})
        self.info = ImageInfo(app=None, src_img_fp=fp, src_format=fmt)
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
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = NooneAuthorizer({})
        self.info = ImageInfo(app=None, src_img_fp=fp, src_format=fmt)
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
        fp = "img/test.png"
        fmt = "png"
        self.authorizer = SingleDegradingAuthorizer({})
        self.badInfo = ImageInfo(app=None, src_img_fp=fp, src_format=fmt)
        self.okayIdent = "67352ccc-d1b0-11e1-89ae-279075081939.jp2"
        self.okayInfo = ImageInfo(app=None, src_img_fp="img/%s" % self.okayIdent, src_format="jp2")
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
        fp = "img/test.png"
        fmt = "png"

        self.authorizer = RulesAuthorizer(
            {"cookie_secret": b"4rakTQJDyhaYgoew802q78pNnsXR7ClvbYtAF1YC87o=",
            "token_secret": b"hyQijpEEe9z1OB9NOkHvmSA4lC1B4lu1n80bKNx0Uz0=",
            "salt": b"4rakTQJD4lC1B4lu"})
        self.badInfo = ImageInfo(app=None, src_img_fp=fp, src_format=fmt)
        self.okayIdent = "67352ccc-d1b0-11e1-89ae-279075081939.jp2"
        self.okayInfo = ImageInfo(app=None, src_img_fp="img/%s" % self.okayIdent, src_format="jp2")

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

        self.tokenRequest = MockRequest(
            headers={"Authorization": b"Bearer " + tv, "origin": self.origin}
        )
        self.cookieRequest = MockRequest(
            headers={"origin": self.origin}, cookies={'iiif_access_cookie': cv}
        )
        self.cookieRequest.path = ".../default.jpg"

        self.jwtTokenRequest = MockRequest(
            headers={"Authorization": b"Bearer " + jwt_tv, "origin": self.origin}
        )
        self.jwtCookieRequest = MockRequest(
            headers={"origin": self.origin}, cookies={'iiif_access_cookie': jwt_cv}
        )
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


InfoStub = collections.namedtuple("InfoStub", ["auth_rules"])


class TestRulesAuthorizerPytest:

    @staticmethod
    def create_authorizer(**extra_config):
        config = {
            "cookie_secret": "123",
            "token_secret": b"123",
        }
        config.update(extra_config)

        return RulesAuthorizer(config=config)

    @pytest.mark.parametrize("config, expected_error", [
        (
            {
                "cookie_service": "cookie.example.com",
                "token_service": "token.example.com",
                "token_secret": b"t0k3ns3kr1t"
            },
            "Missing mandatory parameters for RulesAuthorizer: cookie_secret"
        ),
        (
            {
                "cookie_service": "cookie.example.com",
                "token_service": "token.example.com",
                "cookie_secret": "c00ki3sekr1t",
            },
            "Missing mandatory parameters for RulesAuthorizer: token_secret"
        ),
        (
            {
                "cookie_service": "cookie.example.com",
                "token_service": "token.example.com",
                "cookie_secret": "c00ki3sekr1t",
                "token_secret": b"t0k3ns3kr1t",
                "use_jwt": False,
            },
            'If use_jwt=False, you must supply the "salt" config parameter'
        ),
        (
            {
                "cookie_service": "cookie.example.com",
                "token_service": "token.example.com",
                "cookie_secret": "c00ki3sekr1t",
                "token_secret": u"t0k3ns3kr1t",
                "use_jwt": False,
                "salt": u"salt",
            },
            '"token_secret" config parameter must be bytes;'
        ),
        (
            {
                "cookie_service": "cookie.example.com",
                "token_service": "token.example.com",
                "cookie_secret": "c00ki3sekr1t",
                "token_secret": b"t0k3ns3kr1t",
                "use_jwt": False,
                "salt": u"salt",
            },
            '"salt" config parameter must be bytes;'
        ),
    ])
    def test_invalid_config_is_configerror(self, config, expected_error):
        with pytest.raises(ConfigError, match=expected_error):
            RulesAuthorizer(config)

    @pytest.mark.parametrize("auth_rules, expected_is_protected", [
        ({}, False),
        ({"allowed": []}, False),
        ({"allowed": ["yes"]}, True),
    ])
    def test_is_protected(self, auth_rules, expected_is_protected):
        info = InfoStub(auth_rules=auth_rules)
        authorizer = self.create_authorizer()
        assert authorizer.is_protected(info=info) == expected_is_protected

    def test_no_allowed_in_auth_rules_is_always_authorized(self):
        info = InfoStub(auth_rules={})
        authorizer = self.create_authorizer()
        assert authorizer.is_authorized(info=info, request=None) == {"status": "ok"}

    @pytest.mark.parametrize("bad_token", [
        jwt.encode({}, b"different_token_secret-localhost", algorithm="HS256"),
        jwt.encode({}, b"token_secret-different_origin", algorithm="HS256"),
        jwt.encode(
            {"exp": datetime.datetime(2001, 1, 1)},
            b"token_secret-localhost",
            algorithm="HS256"
        ),
    ])
    def test_failed_jwt_verification_is_deny(self, bad_token):
        info = InfoStub(auth_rules={"allowed": ["any"]})
        authorizer = self.create_authorizer(
            token_secret=b"token_secret",
            use_jwt=True
        )

        headers = {
            "Authorization": b"Bearer " + bad_token,
            "Origin": "localhost",
        }

        request = MockRequest(headers=headers)

        assert (
            authorizer.is_authorized(info=info, request=request) == {"status": "deny"}
        )
