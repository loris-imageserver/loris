# -*- coding: utf-8 -*-
"""
`authorizer` -- Handle authorization of access to content
=========================================================
"""

from logging import getLogger
from loris_exception import AuthorizerException
import requests

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
        for (k, v) in svc.items():
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

    def is_authorized(self, info, cookie="", token=""):
        """

        Args:
            info (ImageInfo):
                The ImageInfo description of the image
        KWArgs:
            cookie (str):
                The cookie value from the request for an image
            token (str):
                The token value from the Authorization header for info.json
        Returns:
            {"status": "ok / deny / redirect", "location": "uri-to-redirect-to"}

        """
        cn = self.__class__.__name__
        raise NotImplementedError('is_authorized() not implemented for %s' % (cn,))

class NullAuthorizer(_AbstractAuthorizer):
    """
    Everything is permissible
    """

    def __init__(self, config):
        super(NullAuthorizer, self).__init__(config)
 
    def is_protected(self, info):
        return False

    def is_authorized(self, info, cookie="", token=""):
        # Should never be called
        return {"status": "ok"}

    def get_services_info(self, info):
        # No services needed, return empty dict
        return {}

class NooneAuthorizer(_AbstractAuthorizer):
    """
    Everything is forbidden
    """

    def __init__(self, config):
        super(NooneAuthorizer, self).__init__(config)
 
    def is_protected(self, info):
        return True

    def is_authorized(self, info, cookie="", token=""):
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

    def is_authorized(self, info, cookie="", token=""):
        # Assumes a trivial resolver
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
        r = requests.post(self.protected_url, data={"id":info.ident, "fp":info.src_img_fp})

    def is_authorized(self, info, cookie="", token=""):
        r = requests.post(self.authorized_url, data={"id":info.ident, 
            "fp":info.src_img_fp, "cookie":cookie, "token": token})

    def get_services_info(self, info):
        r = requests.post(self.services_url, data={"id":info.ident, "fp":info.src_img_fp})

class RulesAuthorizer(_AbstractAuthorizer):

    def __init__(self, config):
        super(RulesAuthorizer, self).__init__(config)

    def is_protected(self, info):
        pass

    def is_authorized(self, info, cookie="", token=""):
        pass

    def get_services_info(self, info):
        pass

