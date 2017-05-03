# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""

from logging import getLogger
from loris_exception import AuthorizerException

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
        raise NotImplementedError('is_resolvable() not implemented for %s' % (cn,))

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
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))

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
        Raises:
            ResolverException when something goes wrong...
        """
        cn = self.__class__.__name__
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))

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
        # No services needed
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
        tmpl['label'] = "Go Away"
        tmpl['profile'] = self.login_profile
        self._strip_empty_fields(tmpl)
        token = self.service_template.copy()
        token['@id'] = "http://.../error_token"
        token['label'] = "No really, go away"
        token['profile'] = self.token_profile
        self._strip_empty_fields(token)

        tmpl['service'] = [token]
        return {"service": tmpl}

class TestDegradingAuthorizer(_AbstractAuthorizer):
    """
    Everything is the test image, except the test image
    """
    def is_protected(self, info):
        return not info.src_img_fp.endswith('67352ccc-d1b0-11e1-89ae-279075081939.jp2')

    def is_authorized(self, info, cookie="", token=""):
        return {"status": "redirect", 
            "location": "67352ccc-d1b0-11e1-89ae-279075081939.jp2/info.json"}    

    def get_services_info(self, info):
        tmpl = self.service_template.copy()
        tmpl['@id'] = "http://.../degraded"
        tmpl['label'] = "Go over there"
        tmpl['profile'] = self.login_profile
        self._strip_empty_fields(tmpl)
        token = self.service_template.copy()
        token['@id'] = "http://.../error_token"
        token['label'] = "No really, go over there"
        token['profile'] = self.token_profile
        self._strip_empty_fields(token)
        tmpl['service'] = [token]
        return {"service": tmpl}
