
from bottle import request, response, abort, redirect
from bottle import auth_basic, parse_auth, Bottle, run
from bottle import debug as set_debug

import json

# XXX These probably aren't 3.x safe
import urllib, urllib2

class AuthApp(object):

    def __init__(self):
        self.AUTH_URL_LOGIN = "login"
        self.AUTH_URL_COOKIE = "cookie"
        self.AUTH_URL_TOKEN = "token"
        self.AUTH_URL_LOGOUT = "logout"

        self.handler = BasicAuthHandler(self)

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

    def __init__(self, app, name="iiif_access_cookie", secret="abc123"):
        self.application = app
        self.cookie_name = name
        self.cookie_secret = secret

    def cookie_to_token(self, cookie):
        return cookie

    def make_secret(self, origin='*'):
        return "{0}-{1}".format(self.cookie_secret, origin)

    def token(self):
        # This is the second step -- client requests a token to send to info.json
        # We're going to just copy it from our cookie.
        # postMessage request to get the token to send to info.json in Auth'z header
        msgId = request.query.get('messageId', '')
        origin = request.query.get('origin', '*')
        secret = self.make_secret(origin)
        try:
            account = request.get_cookie(self.cookie_name, secret=secret)
        except:
            account = ''
        if not account:
            data = {"error":"missingCredentials","description":"No login details received"}
        else:
            token = self.cookie_to_token(account)
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
        response.delete_cookie(self.cookie_name)
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
        who, p = parse_auth(auth)      
        origin = request.query.get('origin', '*')
        secret = self.make_secret(origin)
        response.set_cookie(self.cookie_name, who, secret=secret)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html", );

class OAuthHandler(AuthNHandler):

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
            'state': request.query.get('next'),
        }
        url = self.GOOGLE_OAUTH2_URL + 'auth?' + urllib.urlencode(params)
        response['Access-Control-Allow-Origin'] = '*'
        redirect(url)

    def cookie(self):
        # OAuth ends up back here from Google. This sets a cookie and closes window
        # to trigger next step
        resp = self._get_token()
        data = self._get_data(resp)

        first = data.get('given_name', '')
        last = data.get('family_name', '')
        email = data.get('email', '')
        name = data.get('name', '')
        pic = data.get('picture', '')
        secret = self.make_secret(origin)
        response.set_cookie(self.cookie_name, email, secret=secret)
        return self.application.send("<html><script>window.close();</script></html>", ct="text/html");


def main():
    host = "localhost"
    port = 8000
    authapp = AuthApp()
    app=authapp.get_bottle_app()

    set_debug(True)
    run(host=host, port=port, app=app)

if __name__ == "__main__":
    main()
else:
    app = AuthApp();
    application = app.get_bottle_app()
