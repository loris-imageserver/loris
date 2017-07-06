from bottle import request, response, abort, redirect
from bottle import auth_basic, parse_auth, Bottle, run
from bottle import debug as set_debug
import json
import sys

# XXX These probably aren't Python 3.x safe?
import urllib, urllib2
from netaddr import IPNetwork, IPAddress


# XXX FixMe to do real encryption!
def encrypt(clear, key):
    return clear

def decrypt(enc, key):
    return enc
   
class AuthApp(object):

    def __init__(self):
        self.AUTH_URL_LOGIN = "login"
        self.AUTH_URL_COOKIE = "cookie"
        self.AUTH_URL_TOKEN = "token"
        self.AUTH_URL_LOGOUT = "logout"
        # login:
        # self.handler = BasicAuthHandler(self)
        # self.handler = OAuthHandler(self)
        # kiosk:
        self.handler = IPRangeHandler(self)

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

    def __init__(self, app, name="iiif_access_cookie", cookie_secret="abc123", token_secret="xyz987"):
        self.application = app
        self.cookie_name = name
        self.cookie_secret = cookie_secret
        self.token_secret = token_secret
        self.ENCRYPT_TOKEN = True

    def origin_to_secret(self, origin):
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

    def cookie_to_token(self, cookie):
        return cookie

    def make_secret(self, origin='*', which="cookie"):
        # Reduce origin to just domain
        reqsecret = self.origin_to_secret(origin)
        svrsecret = self.cookie_secret if which == "cookie" else self.token_secret
        return "{0}-{1}".format(svrsecret, reqsecret)

    def token(self):
        # This is the second step -- client requests a token to send to info.json
        # We're going to just copy it from our cookie.
        # postMessage request to get the token to send to info.json in Auth'z header
        msgId = request.query.get('messageId', '')
        origin = request.query.get('origin', '*')
        secret = self.make_secret(origin, "cookie")
        try:
            account = request.get_cookie(self.cookie_name)
            account = decrypt(account, secret)
            response.set_cookie(self.cookie_name, account)
        except:
            account = ''
        if not account:
            data = {"error":"missingCredentials","description":"No login details received"}
        else:
            # This is okay, as they're differently salted
            token = self.cookie_to_token(account)

            if self.ENCRYPT_TOKEN:
                # encrypt token
                secret2 = self.make_secret(origin, "token")
                token = encrypt(token, secret2)
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
        response.delete_cookie(self.cookie_name, domain="getty.edu", path="/")
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
        secret = self.make_secret(origin, "cookie")
        value = encrypt(who, secret)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html", );

class IPRangeHandler(AuthNHandler):

    def __init__(self, app, name="iiif_access_cookie", cookie_secret="abc123", token_secret="xyz987"):
        self.application = app
        self.cookie_name = name
        self.cookie_secret = cookie_secret
        self.token_secret = token_secret
        self.ENCRYPT_TOKEN = True

        self.network = IPNetwork("10.0.0.0/16")
        self.exclude = [IPAddress("10.0.0.1")]

    def login(self):
        # Check if IP of browser is acceptable
        reqip = IPAddress(request.environ.get("REMOTE_ADDR"))
        if reqip in self.network and not reqip in self.exclude:
            origin = request.query.get('origin', '*')        
            secret = self.make_secret(origin, "cookie")
            value = encrypt("on-site", secret)
            # secure=True to limit to only https connections
            response.set_cookie(self.cookie_name, value, domain="getty.edu", path="/", httponly=True)
            return self.application.send("<html><script>window.close();</script><body>%s</body></html>" % reqip, ct="text/html")
        else:
            return self.application.send("<html><body>Message for requiring on-site access here</body></html>", status=403, ct="text/html")


class OAuthHandler(AuthNHandler):

    def __init__(self, app, name="iiif_access_cookie", cookie_secret="abc123", token_secret="xyz987"):
        self.application = app
        self.cookie_name = name
        self.cookie_secret = cookie_secret
        self.token_secret = token_secret
        self.cookie_domain = ""
        self.ENCRYPT_TOKEN = True
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
        payload = urllib.urlencode(params)
        url = self.GOOGLE_OAUTH2_URL + 'token'
        req = urllib2.Request(url, payload) 
        return json.loads(urllib2.urlopen(req).read())

    def _get_data(self, response):
        params = {
            'access_token': response['access_token'],
        }
        payload = urllib.urlencode(params)
        url = self.GOOGLE_API_URL + 'userinfo?' + payload
        req = urllib2.Request(url)  # must be GET
        return json.loads(urllib2.urlopen(req).read())

    def login(self):
        # OAuth starts here. This will redirect User to Google
        origin = request.query.get('origin', '*')
        params = {
            'response_type': 'code',
            'client_id': self.GOOGLE_API_CLIENT_ID,
            'redirect_uri': self.GOOGLE_REDIRECT_URI,
            'scope': self.GOOGLE_API_SCOPE,
            'state': request.query.get('origin'),
        }
        url = self.GOOGLE_OAUTH2_URL + 'auth?' + urllib.urlencode(params)
        response['Access-Control-Allow-Origin'] = '*'
        redirect(url)

    def cookie(self):
        # OAuth ends up back here from Google. This sets a cookie and closes window
        # to trigger next step
        origin = request.query.get('state', '')
        resp = self._get_token()
        data = self._get_data(resp)

        first = data.get('given_name', '')
        last = data.get('family_name', '')
        email = data.get('email', 'foo')
        name = data.get('name', '')
        pic = data.get('picture', '')
        secret = self.make_secret(origin, "cookie")
        value = encrypt(email, secret)

        # secure=True to limit to only https connections
        response.set_cookie(self.cookie_name, value, domain=self.cookie_domain, path="/", httponly=True)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html");


def main():
    host = "media.getty.edu"
    port = 80
    authapp = AuthApp()
    app=authapp.get_bottle_app()

    set_debug(True)
    run(host=host, port=port, app=app)

if __name__ == "__main__":
    main()
else:
    app = AuthApp();
    application = app.get_bottle_app()
