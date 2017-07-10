from bottle import request, response, abort, redirect
from bottle import auth_basic, parse_auth, Bottle, run
from bottle import debug as set_debug
import json
import sys

try:
    from urllib import urlencode
    from urllib2 import Request, urlopen
except ImportError: 
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

try:
    from netaddr import IPNetwork, IPAddress
except ImportError:
    # The IP authentication class just won't work without this
    # but others will be fine
    pass

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# cryptography is MUCH faster than simplecrypt
# to the point of not even being worth writing a simplecrypt wrapper
# pycrypto functions could be used, but most require a specific blocksize
# PKCS1_OAEP doesn't, but does need a full on RSA key
# Others could be used with some padding
# But Fernet seems fine :)
   
class AuthApp(object):

    def __init__(self, cookie_secret, token_secret, salt, name="iiif_access_cookie",
            cookie_domain="", cookie_path="", is_https=True):
        self.AUTH_URL_LOGIN = "login"
        self.AUTH_URL_COOKIE = "cookie"
        self.AUTH_URL_TOKEN = "token"
        self.AUTH_URL_LOGOUT = "logout"
        # login:
        # self.handler = BasicAuthHandler(self)
        # self.handler = OAuthHandler(self)
        self.handler = IPRangeHandler(self, cookie_secret, token_secret, salt, name,
            cookie_domain, cookie_path, is_https)

    def send(self, data, status=200, ct="text/plain"):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = "GET,OPTIONS"
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Authorization'
        response["content_type"] = ct
        response.status = status
        return data

    def not_implemented():
        abort(501)

    def dispatch_views(self):
        # Handle getting user to log in
        self.app.route('/{0}'.format(self.AUTH_URL_LOGIN), ["GET"], 
            getattr(self.handler, "login", self.not_implemented))               

        # Give back a cookie and close window
        # Also where user comes back to after OAuth
        self.app.route('/{0}'.format(self.AUTH_URL_COOKIE), ["GET"], 
            getattr(self.handler, "cookie", self.not_implemented))

        # PostMessage() or return a token
        self.app.route('/{0}'.format(self.AUTH_URL_TOKEN), ["GET"], 
            getattr(self.handler, "token", self.not_implemented))

        # Let the user logout
        if self.AUTH_URL_LOGOUT:
            self.app.route('/{0}'.format(self.AUTH_URL_LOGOUT), ["GET"], 
                getattr(self.handler, "logout", self.not_implemented)) 

    def get_bottle_app(self):
        """Returns bottle instance"""
        self.app = Bottle()
        self.dispatch_views()
        return self.app    


class AuthNHandler(object):

    def __init__(self, app, cookie_secret, token_secret, salt, name="iiif_access_cookie",
            cookie_domain="", cookie_path="", is_https=True):
        self.application = app
        self.cookie_name = name
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.is_https = is_https
        self.cookie_secret = cookie_secret
        self.token_secret = token_secret
        self.salt = salt

    def kdf(self):
       return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self.salt,
            iterations=100000, backend=default_backend())

    @staticmethod
    def basic_origin(origin):
        ccslds = ['co', 'org', 'com', 'net', 'ac', 'edu', 'gov', 'mil', 'or', \
            'gen', 'govt', 'school', 'sch']
        origin = origin.replace('https://', '')
        origin = origin.replace('http://', '') # Mixed Content violation
        slidx = origin.find("/")
        if slidx > -1:
            origin = origin[:slidx]
        cidx = origin.find(":")
        if cidx > -1:
            origin = origin[:cidx]
        domain = origin.split('.')
        if len(domain) >= 3 and domain[-2] in ccslds:
            # foo.x.cctld
            secret = ".".join(domain[-3:])
        elif len(domain) >= 2:
            # foo.gtld
            secret = ".".join(domain[-2:])
        else:
            # localhost or * ... hopefully not *!
            secret = domain
        return secret

    def set_cookie(self, value, origin, response):
        origin = self.basic_origin(origin)
        secret = "%s-%s" % (self.cookie_secret, origin)        
        key = base64.urlsafe_b64encode(self.kdf().derive(secret))
        fern = Fernet(key)
        value = fern.encrypt("%s|%s" % (origin, value))
        response.set_cookie(self.cookie_name, value, domain=self.cookie_domain, 
            path=self.cookie_path, httponly=True, secure=self.is_https)

    def cookie_to_token(self, cookie):
        # this is okay, so long as the encryption keys are different
        return cookie

    def token(self):
        # This is the second step -- client requests a token to send to info.json
        # We're going to just copy it from our cookie.
        # postMessage request to get the token to send to info.json in Auth'z header
        msgId = request.query.get('messageId', '')
        origin = request.query.get('origin', '*')
        origin = self.basic_origin(origin)

        try:
            info = request.get_cookie(self.cookie_name)
            secret = "%s-%s" % (self.cookie_secret, origin)        
            key = base64.urlsafe_b64encode(self.kdf().derive(secret))
            fern = Fernet(key)
            value = fern.decrypt(info)
        except:
            info = ''

        if not info:
            data = {"error":"missingCredentials","description":"No login details received"}
        elif not info.startswith(origin):
            # Hmmm... hack attempt?
            data = {"error":"invalidCredentials","description":"Login details invalid"}
        else:
            token = self.cookie_to_token(info)
            secret = "%s-%s" % (self.token_secret, origin)        
            key = base64.urlsafe_b64encode(self.kdf().derive(secret))
            fern = Fernet(key)
            value = fern.encrypt(token)
            data = {"accessToken":token, "expiresIn": 3600}

        if msgId:
            data['messageId'] = msgId
            dataStr = json.dumps(data)
            html = """<html><body><script>
window.parent.postMessage({0}, '{1}');
</script></body></html>""".format(dataStr, origin)
            return self.application.send(html, ct="text/html")
        else:
            dataStr = json.dumps(data)
            return self.application.send(dataStr, ct="application/json")

    def logout(self):
        response.delete_cookie(self.cookie_name, domain=self.cookie_domain, path=self.cookie_path)
        response['Access-Control-Allow-Origin'] = '*'
        return self.application.send("<html><script>window.close();</script></html>", status=401, ct="text/html"); 


class BasicAuthHandler(AuthNHandler):
    def check_basic_auth(user, password):
        # Re-implement me to do actual user/password checking
        return user == password

    @auth_basic(check_basic_auth)
    def login(self):
        origin = request.query.get('origin', '*')        
        redirect("cookie?origin={0}".format(origin))

    def cookie(self):
        auth = request.headers.get('Authorization')
        if not auth:
            return self.application.send("<html><script>window.close();</script></html>", ct="text/html", );
        who, p = parse_auth(auth)      
        origin = request.query.get('origin', '*')
        self.set_cookie(who, origin, response)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html", );

class IPRangeHandler(AuthNHandler):

    def __init__(self, app, cookie_secret, token_secret, salt, name="iiif_access_cookie",
            cookie_domain="", cookie_path="", is_https=True):
        super(IPRangeHandler,self).__init__(app, cookie_secret, token_secret, salt, name,
            cookie_domain, cookie_path, is_https)

        self.network = IPNetwork("10.0.0.0/16")
        self.exclude = [IPAddress("10.0.0.1")]

    def login(self):
        # Check if IP of browser is acceptable
        reqip = IPAddress(request.environ.get("REMOTE_ADDR"))
        if reqip in self.network and not reqip in self.exclude:
            origin = request.query.get('origin', '*')
            self.set_cookie("on-site", origin, response)
            return self.application.send("<html><script>window.close();</script><body>%s</body></html>" % reqip, ct="text/html")
        else:
            return self.application.send("<html><body>Message for requiring on-site access here</body></html>", status=403, ct="text/html")


class OAuthHandler(AuthNHandler):

    def __init__(self, app, cookie_secret, token_secret, salt, name="iiif_access_cookie",
            cookie_domain="", cookie_path="", is_https=True):
        super(OAuthHandler,self).__init__(app, cookie_secret, token_secret, salt, name,
            cookie_domain, cookie_path, is_https)

        self.GOOGLE_API_CLIENT_ID = ""
        self.GOOGLE_API_CLIENT_SECRET = ""
        self.GOOGLE_REDIRECT_URI = ""
        self.GOOGLE_OAUTH2_URL = "https://accounts.google.com/o/oauth2/"
        self.GOOGLE_API_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
        self.GOOGLE_API_URL = "https://www.googleapis.com/oauth2/v1/"

    def _get_token(self):
        params = {
            'code': request.query.get('code'),
            'client_id': self.GOOGLE_API_CLIENT_ID,
            'client_secret': self.GOOGLE_API_CLIENT_SECRET,
            'redirect_uri': self.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
        payload = urlencode(params)
        url = self.GOOGLE_OAUTH2_URL + 'token'
        req = Request(url, payload) 
        return json.loads(urlopen(req).read())

    def _get_data(self, response):
        params = {
            'access_token': response['access_token'],
        }
        payload = urlencode(params)
        url = self.GOOGLE_API_URL + 'userinfo?' + payload
        req = Request(url)  # must be GET
        return json.loads(urlopen(req).read())

    def login(self):
        # OAuth starts here. This will redirect User to Google to authenticate
        origin = request.query.get('origin', '*')
        params = {
            'response_type': 'code',
            'client_id': self.GOOGLE_API_CLIENT_ID,
            'redirect_uri': self.GOOGLE_REDIRECT_URI,
            'scope': self.GOOGLE_API_SCOPE,
            'state': request.query.get('origin'),
        }
        url = self.GOOGLE_OAUTH2_URL + 'auth?' + urlencode(params)
        response['Access-Control-Allow-Origin'] = '*'
        redirect(url)

    def cookie(self):
        # OAuth ends up back here from Google. This sets a cookie and closes window
        # to trigger next step
        origin = request.query.get('state', '')
        resp = self._get_token()
        data = self._get_data(resp)

        # Other info in data are: given_name, family_name, name, picture, ...
        email = data.get('email', 'noone@nowhere')
        self.set_cookie(email, origin, response)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html");


def main():
    host = "localhost"
    port = 8080
    # These are the test keys, replace with real ones!
    k1 = "4rakTQJDyhaYgoew802q78pNnsXR7ClvbYtAF1YC87o="
    k2 = "hyQijpEEe9z1OB9NOkHvmSA4lC1B4lu1n80bKNx0Uz0="
    salt = "4rakTQJD4lC1B4lu"
    authapp = AuthApp(k1, k2, salt, is_https=False)
    app=authapp.get_bottle_app()

    set_debug(True)
    run(host=host, port=port, app=app)

if __name__ == "__main__":
    main()
else:
    app = AuthApp();
    application = app.get_bottle_app()
