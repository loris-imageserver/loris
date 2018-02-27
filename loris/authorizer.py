# -*- coding: utf-8 -*-
"""
`authorizer` -- Handle authorization of access to content
=========================================================
"""
from __future__ import absolute_import

from logging import getLogger
import requests

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse

import jwt

# See: https://cryptography.io/en/latest/fernet/#using-passwords-with-fernet
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .loris_exception import AuthorizerException, ConfigError

logger = getLogger(__name__)

class _AbstractAuthorizer(object):

    def __init__(self, config):
        self.config = config
        self.cookie_name = config.get('cookie_name', 'iiif_access_cookie')
        self.service_template = {
            "@context": "http://iiif.io/api/auth/1/context.json",
            "@id": "",
            "profile": "",
            "label": "",
            "header": "",
            "description": "",
            "confirmLabel": "",
            "failureHeader": "",
            "failureDescription": "",
            "service": []
        }

        self.login_profile = "http://iiif.io/api/auth/1/login"
        self.clickthrough_profile = "http://iiif.io/api/auth/1/clickthrough"
        self.kiosk_profile = "http://iiif.io/api/auth/1/kiosk"
        self.external_profile = "http://iiif.io/api/auth/1/external"
        self.token_profile = "http://iiif.io/api/auth/1/token"


    def _strip_empty_fields(self, svc):
        # dicts are modified in place
        for k, v in list(svc.items()):
            if not v:
                del svc[k]

    def is_protected(self, info):
        """

        Args:
            info (ImageInfo):
                The ImageInfo description of the image
        Returns:
            bool
        """
        cn = self.__class__.__name__
        raise NotImplementedError('is_protected() not implemented for %s' % (cn,))

    def get_services_info(self, info):
        """

        Args:
            info (ImageInfo):
                The ImageInfo description of the image
        Returns:
            {"services": {...}}
        Raises:
            ResolverException when something goes wrong...
        """
        cn = self.__class__.__name__
        raise NotImplementedError('get_services_info() not implemented for %s' % (cn,))

    def is_authorized(self, info, request):
        """

        Args:
            info (ImageInfo):
                The ImageInfo description of the image
            request (Request):
                The wsgi request object
        Returns:
            {"status": "ok / deny / redirect", "location": "uri-to-redirect-to"}

        """
        cn = self.__class__.__name__
        raise NotImplementedError('is_authorized() not implemented for %s' % (cn,))

class NullAuthorizer(_AbstractAuthorizer):
    """
    Everything is permissible
    """
    def is_protected(self, info):
        return False

    def is_authorized(self, info, request):
        # Should never be called
        return {"status": "ok"}

    def get_services_info(self, info):
        # No services needed, return empty dict
        return {}

class NooneAuthorizer(_AbstractAuthorizer):
    """
    Everything is forbidden
    """
    def is_protected(self, info):
        return True

    def is_authorized(self, info, request):
        return {"status": "deny"}

    def get_services_info(self, info):
        tmpl = self.service_template.copy()
        tmpl['@id'] = "http://.../denied"
        tmpl['label'] = "Please Go Away"
        tmpl['profile'] = self.login_profile
        self._strip_empty_fields(tmpl)
        token = self.service_template.copy()
        token['@id'] = "http://.../error_token"
        token['label'] = "No really, please go away"
        token['profile'] = self.token_profile
        self._strip_empty_fields(token)
        tmpl['service'] = [token]
        return {"service": tmpl}

class SingleDegradingAuthorizer(_AbstractAuthorizer):
    """
    Everything degrades to the configured image, except the configured image
    """
    def __init__(self, config):
        super(SingleDegradingAuthorizer, self).__init__(config)
        self.redirect_fp = config.get('redirect_target', 
            '67352ccc-d1b0-11e1-89ae-279075081939.jp2')

    def is_protected(self, info):
        return not info.src_img_fp.endswith(self.redirect_fp)

    def is_authorized(self, info, request):
        # Won't be called for the redirect img, as it's not protected
        return {"status": "redirect", 
            "location": "%s/info.json" % self.redirect_fp}    

    def get_services_info(self, info):
        tmpl = self.service_template.copy()
        tmpl['@id'] = "http://.../degraded"
        tmpl['label'] = "Please go over there"
        tmpl['profile'] = self.login_profile
        self._strip_empty_fields(tmpl)
        token = self.service_template.copy()
        token['@id'] = "http://.../error_token"
        token['label'] = "No really, please go over there"
        token['profile'] = self.token_profile
        self._strip_empty_fields(token)
        tmpl['service'] = [token]
        return {"service": tmpl}


class RulesAuthorizer(_AbstractAuthorizer):

    def __init__(self, config):
        super(RulesAuthorizer, self).__init__(config)
        self._validate_config(config)

        self.cookie_service = config.get('cookie_service', "")
        self.token_service = config.get('token_service', "")
        self.cookie_secret = config['cookie_secret']
        self.token_secret = config['token_secret']

        self.use_jwt = config.get('use_jwt', True)
        self.salt = config.get('salt', b'')
        self.roles_key = config.get('roles_key', 'roles')
        self.id_key = config.get('id_key', 'sub')

    def _validate_config(self, config):
        mandatory_keys = ['cookie_secret', 'token_secret']
        missing_keys = [key for key in mandatory_keys if key not in config]

        if missing_keys:
            raise ConfigError(
                'Missing mandatory parameters for %s: %s' %
                (type(self).__name__, ','.join(missing_keys))
            )

        if not config.get('use_jwt', True) and ('salt' not in config):
            raise ConfigError(
                'If use_jwt=%r, you must supply the "salt" config parameter' %
                config['use_jwt']
            )

        if ('salt' in config) and (not isinstance(config['salt'], bytes)):
            raise ConfigError('"salt" config parameter must be bytes; got %r (%s)' % (config['salt'], type(config['salt'])))

    def kdf(self):
        return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self.salt,
            iterations=100000, backend=default_backend())

    @staticmethod
    def basic_origin(origin):
        ccslds = ['co', 'org', 'com', 'net', 'ac', 'edu', 'gov', 'mil', 'or', \
            'gen', 'govt', 'school', 'sch']
        if not origin.startswith('http'):
            origin = "http://" + origin
        u = urlparse(origin)
        domain = u.hostname.split('.')

        if len(domain) >= 3 and domain[-2] in ccslds:
            # foo.x.cctld
            secret = ".".join(domain[-3:])
        elif domain[-1].isdigit():
            # 10.0.0.1
            secret = u.hostname
        elif len(domain) >= 2:
            # foo.gtld
            secret = ".".join(domain[-2:])
        else:
            # localhost or * ... hopefully not *!
            secret = domain[0]
        return secret

    def _get_roles_for_identity(self, value):
        return [value]

    def _roles_from_value(self, value):
        if type(value) == dict:            
            # JWT
            roles = value.get(self.roles_key, [])
            if not roles:
                return self._get_roles_for_identity(value.get(self.id_key, ''))
            return roles
        else:
            # assume that our value is an identity not a role
            return self._get_roles_for_identity(value)

    def _roles_from_request(self, request):

        ### Use request to determine type of request

        origin = request.headers.get('origin', '')
        if not origin:
            origin = request.headers.get('referer', '*')
        origin = self.basic_origin(origin).encode('utf8')

        logger.debug('Got basic origin: %s', origin)
        
        if request.path.endswith('info.json'):
            token = request.headers.get('Authorization', '')        
            if not isinstance(token, bytes):
                logger.warning('encoding Authorization header as utf8')
                token = token.encode('utf8')
            token = token.replace(b'Bearer', b'')
            cval = token.strip()
            if not cval:
                return []
            secret = b'-'.join([self.token_secret, origin])
        else:
            cval = request.cookies.get(self.cookie_name)
            if not cval:
                return []
            secret = b'-'.join([self.cookie_secret, origin])

        if not isinstance(cval, bytes):
            cval = cval.encode('utf8')

        if self.use_jwt:
            try:
                value = jwt.decode(cval, secret)
            except jwt.ExpiredSignatureError:
                value = jwt.decode(cval, secret, verify=False)                
                logger.debug(value)
                raise AuthorizerException(message="invalidCredentials: expired")
        else:
            key = base64.urlsafe_b64encode(self.kdf().derive(secret))
            fern = Fernet(key)
            value = fern.decrypt(cval)
            if not value.startswith(origin):
                # Cookie/Token theft
                return []
            else:
                value = value[len(origin)+1:]

        try:
            value = value.decode('utf8')
        except AttributeError:
            pass
        roles = self._roles_from_value(value)
        return roles

    def find_best_tier(self, tiers, userroles):
        for t in tiers:
            roles = t.get('allowed', [])
            if not roles:
                # public tier
                return t['identifier']
            okay = set(roles).intersection(userroles)            
            if okay:
                # user is allowed to see this tier
                return t['identifier']
        # No tier is possible with current roles, deny
        return ""

    def is_protected(self, info):
        # Now we can check info.auth_rules
        # Protected if there's an 'allowed' key, with a non-false value 
        logger.debug("Called is_protected with %r" % info.auth_rules)
        return bool('allowed' in info.auth_rules and info.auth_rules['allowed'])

    def is_authorized(self, info, request):
        if not "allowed" in info.auth_rules:
            # We shouldn't be here, but just check in case
            return {"status": "ok"}

        roles = info.auth_rules['allowed']

        try:
            userroles = set(self._roles_from_request(request))
        except AuthorizerException as e:
            logger.debug("Got authorization exception: %s" % e.message)
            return {"status": "deny"}

        okay = set(roles).intersection(userroles)
        logger.debug("roles: %r  // user: %r // intersection: %r" % (roles, userroles, okay))

        if okay:
            return {"status": "ok"}
        else:
            loc = self.find_best_tier(info.auth_rules.get('tiers', []), userroles)
            if loc:
                return {"status": "redirect", "location": "%s/info.json" % loc}            
            else:
                return {"status": "deny"} 

    def get_services_info(self, info):

        xi = info.auth_rules.get('extraInfo', {})
        if not xi or not xi.get('service', {}):
            # look in config for URIs instead of in XI
            if not self.cookie_service:
                raise AuthorizerException("No cookie service for authentication")
            elif not self.token_service:
                raise AuthorizerException("No token service for authentication")
            tmpl = self.service_template.copy()
            tmpl['@id'] = self.cookie_service
            tmpl['label'] = "Please Login"
            tmpl['profile'] = self.login_profile
            self._strip_empty_fields(tmpl)
            token = self.service_template.copy()
            token['@id'] = self.token_service
            token['label'] = "Access Token Service"
            token['profile'] = self.token_profile
            self._strip_empty_fields(token)
            tmpl['service'] = [token]
            return {"service": tmpl}
        elif xi and xi.get('service', {}):
            return {"service": xi['service']}
        else:
            raise AuthorizerException("No services for authentication for %s" % info.ident)


class ExternalAuthorizer(_AbstractAuthorizer):
    """
    Pass info through to remote backend system for auth'z business logic
    """

    # Should pass in options/info from resolver!

    def __init__(self, config):
        super(ExternalAuthorizer, self).__init__(config)
        self.authorized_url = config.get('authorized_url', '')
        self.protected_url = config.get('protected_url', '')
        self.services_url = config.get('services_url', '')

    def is_protected(self, info):
        # http://somewhere.org/path/to/service
        # using POST to ensure data doesn't end up in logs
        data = {
            'id': info.ident,
            'fp': info.src_img_fp,
        }
        requests.post(self.protected_url, data=data)

    def is_authorized(self, info, cookie="", token=""):
        data = {
            'id': info.ident,
            'fp': info.src_img_fp,
            'cookie': cookie,
            'token': token,
        }
        requests.post(self.authorized_url, data=data)

    def get_services_info(self, info):
        data = {
            'id': info.ident,
            'fp': info.src_img_fp,
        }
        requests.post(self.services_url, data=data)
