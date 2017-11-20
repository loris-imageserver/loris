# -*- encoding: utf-8 -*-

class LorisException(Exception):
    """Base exception class for all errors raised by Loris."""
    pass


class HTTPException(Exception):
    """Base class for exceptions that are returned as an HTTP response
    to the user.

    See http://iiif.io/api/image/2.1/#error-conditions.

    :param http_status: The HTTP status that should be sent with the
        associated HTTP response.
    :type http_status: int
    :param message: Information about the error.
    :type msg: str

    """
    def __init__(self, http_status, message):
        super(HTTPException, self).__init__(message)
        self.http_status = http_status


class SyntaxException(LorisException, HTTPException):
    pass


class RequestException(LorisException, HTTPException):
    pass


class ImageException(LorisException, HTTPException):
    pass


class ImageInfoException(LorisException, HTTPException):
    pass


class ResolverException(LorisException, HTTPException):
    pass


class TransformException(LorisException, HTTPException):
    pass


class AuthorizerException(LorisException, HTTPException):
    pass


class ConfigError(LorisException):
    """Raised for errors in the user config."""
    pass
