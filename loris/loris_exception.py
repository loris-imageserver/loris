# -*- encoding: utf-8 -*-

class LorisException(Exception):
    """Base exception class for all errors raised by Loris."""
    pass


class SyntaxException(LorisException):
    pass


class RequestException(LorisException):
    pass


class ImageInfoException(LorisException):
    pass


class ResolverException(LorisException):
    pass


class TransformException(LorisException):
    pass


class AuthorizerException(LorisException):
    pass


class ConfigError(LorisException):
    """Raised for errors in the user config."""
    pass
