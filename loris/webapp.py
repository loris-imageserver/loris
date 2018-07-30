#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
webapp.py
=========
Implements IIIF 2.0 <http://iiif.io/api/image/2.0/> level 2
'''
from __future__ import absolute_import

from datetime import datetime
from decimal import getcontext
import logging
from logging.handlers import RotatingFileHandler
import os
from os import path, unlink
import re
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile
try:
    from urllib.parse import unquote, quote_plus
except ImportError:  # Python 2
    from urllib import unquote, quote_plus

import sys
sys.path.append('.')

from configobj import ConfigObj
from werkzeug.http import parse_date, http_date

from werkzeug.wrappers import (
    Request, Response, BaseResponse, CommonResponseDescriptorsMixin
)

from loris import constants, img, transforms
from loris.img_info import InfoCache
from loris.loris_exception import (
    ConfigError,
    ImageInfoException,
    RequestException,
    ResolverException,
    SyntaxException,
    TransformException,
)



getcontext().prec = 25 # Decimal precision. This should be plenty.


def get_debug_config(debug_jp2_transformer):
    # change a few things, read the config and set up logging
    project_dp = path.dirname(path.dirname(path.realpath(__file__)))
    config_file_path = path.join(project_dp, 'etc', 'loris2.conf')

    config = read_config(config_file_path)

    config['logging']['log_to'] = 'console'
    config['logging']['log_level'] = 'DEBUG'

    # override some stuff to look at relative or tmp directories.
    config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
    config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
    config['loris.Loris']['enable_caching'] = True
    config['img.ImageCache']['cache_dp'] = '/tmp/loris/cache/img'
    config['img_info.InfoCache']['cache_dp'] = '/tmp/loris/cache/info'
    config['resolver']['impl'] = 'loris.resolver.SimpleFSResolver'
    config['resolver']['src_img_root'] = path.join(project_dp,'tests','img')
    config['transforms']['target_formats'] = [ 'jpg', 'png', 'gif', 'webp', 'tif']

    if debug_jp2_transformer == 'opj':
        from loris.transforms import OPJ_JP2Transformer
        config['transforms']['jp2']['impl'] = 'OPJ_JP2Transformer'
        opj_decompress = OPJ_JP2Transformer.local_opj_decompress_path()
        config['transforms']['jp2']['opj_decompress'] = path.join(project_dp, opj_decompress)
        libopenjp2_dir = OPJ_JP2Transformer.local_libopenjp2_dir()
        config['transforms']['jp2']['opj_libs'] = path.join(project_dp, libopenjp2_dir)
    elif debug_jp2_transformer == 'kdu':
        from loris.transforms import KakaduJP2Transformer
        config['transforms']['jp2']['impl'] = 'KakaduJP2Transformer'
        kdu_expand = KakaduJP2Transformer.local_kdu_expand_path()
        config['transforms']['jp2']['kdu_expand'] = path.join(project_dp, kdu_expand)
        libkdu_dir = KakaduJP2Transformer.local_libkdu_dir()
        config['transforms']['jp2']['kdu_libs'] = path.join(project_dp, libkdu_dir)
    else:
        raise ConfigError('Unrecognized debug JP2 transformer: %r' % debug_jp2_transformer)

    config['authorizer'] = {'impl': 'loris.authorizer.RulesAuthorizer'}
    config['authorizer']['cookie_secret'] = "4rakTQJDyhaYgoew802q78pNnsXR7ClvbYtAF1YC87o="
    config['authorizer']['token_secret'] = "hyQijpEEe9z1OB9NOkHvmSA4lC1B4lu1n80bKNx0Uz0="
    config['authorizer']['roles_key'] = 'roles'
    config['authorizer']['id_key'] = 'sub'



    return config


def create_app(debug=False, debug_jp2_transformer='kdu', config_file_path=''):
    if debug:
        config = get_debug_config(debug_jp2_transformer)
    else:
        config = read_config(config_file_path)

    return Loris(config)


def read_config(config_file_path):
    config = ConfigObj(config_file_path, unrepr=True, interpolation='template')
    # add the OS environment variables as the DEFAULT section to support
    # interpolating their values into other keys
    # make a copy of the os.environ dictionary so that the config object can't
    # inadvertently modify the environment
    config['DEFAULT'] = {key: val for(key, val) in os.environ.items() if key not in ('PS1')}
    return config


def _validate_logging_config(config):
    """
    Validate the logging config before setting up a logger.
    """
    mandatory_keys = ['log_to', 'log_level', 'format']
    missing_keys = [key for key in mandatory_keys if key not in config]

    if missing_keys:
        raise ConfigError(
            'Missing mandatory logging parameters: %r' %
            ','.join(missing_keys)
        )

    if config['log_to'] not in ('file', 'console'):
        raise ConfigError(
            'logging.log_to=%r, expected one of file/console' % config['log_to']
        )

    if config['log_to'] == 'file':
        mandatory_keys = ['log_dir', 'max_size', 'max_backups']
        missing_keys = []
        for key in mandatory_keys:
            if key not in config:
                missing_keys.append(key)

        if missing_keys:
            raise ConfigError(
                'When log_to=file, the following parameters are required: %r' %
                ','.join(missing_keys)
            )


def configure_logging(config):
    _validate_logging_config(config)

    logger = logging.getLogger()

    try:
        logger.setLevel(config['log_level'])
    except ValueError:
        logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt=config['format'])

    if not getattr(logger, 'handler_set', None):
        if config['log_to'] == 'file':
            fp = '%s.log' % (path.join(config['log_dir'], 'loris'),)
            handler = RotatingFileHandler(fp,
                maxBytes=config['max_size'],
                backupCount=config['max_backups'],
                delay=True)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        elif config['log_to'] == 'console':
            from sys import __stderr__, __stdout__
            # STDERR
            err_handler = logging.StreamHandler(__stderr__)
            err_handler.addFilter(StdErrFilter())
            err_handler.setFormatter(formatter)
            logger.addHandler(err_handler)

            # STDOUT
            out_handler = logging.StreamHandler(__stdout__)
            out_handler.addFilter(StdOutFilter())
            out_handler.setFormatter(formatter)
            logger.addHandler(out_handler)
        else:
            # This should be protected by ``_validate_logging_config()``.
            assert False, "Should not be reachable"

        logger.handler_set = True
    return logger


class StdErrFilter(logging.Filter):
    '''Logging filter for stderr
    '''
    def filter(self,record):
        return 1 if record.levelno >= 30 else 0

class StdOutFilter(logging.Filter):
    '''Logging filter for stdout
    '''
    def filter(self,record):
        return 1 if record.levelno <= 20 else 0

class LorisResponse(BaseResponse, CommonResponseDescriptorsMixin):
    '''Similar to Response, but IIIF Compliance Link and
    Access-Control-Allow-Origin Headers are added and none of the
    ETagResponseMixin, ResponseStreamMixin, or WWWAuthenticateMixin
    capabilities are included.
    See: http://werkzeug.pocoo.org/docs/wrappers/#werkzeug.wrappers.Response
    '''
    def __init__(self, response=None, status=None, content_type=None):
        super(LorisResponse, self).__init__(response=response, status=status, content_type=content_type)
        self.headers['Link'] = '<%s>;rel="profile"' % (constants.COMPLIANCE,)

    def set_acao(self, request, regex=None):
        if regex:
            if regex.search(request.url_root):
                self.headers['Access-Control-Allow-Origin'] = request.url_root
        else:
            self.headers['Access-Control-Allow-Origin'] = "*"
        self.headers['Access-Control-Allow-Methods'] = "GET, OPTIONS"
        self.headers['Access-Control-Allow-Headers'] = "Authorization"


class BadRequestResponse(LorisResponse):
    def __init__(self, message=None):
        if message is None:
            message = "request does not match the IIIF syntax"
        status = 400
        message = 'Bad Request: %s (%d)' % (message, status)
        super(BadRequestResponse, self).__init__(message, status, 'text/plain')

class NotFoundResponse(LorisResponse):
    def __init__(self, message):
        status = 404
        message = 'Not Found: %s (%d)' % (message, status)
        super(NotFoundResponse, self).__init__(message, status, 'text/plain')

class ServerSideErrorResponse(LorisResponse):
    def __init__(self, message):
        status = 500
        message = 'Server Side Error: %s (%d)' % (message, status)
        super(ServerSideErrorResponse, self).__init__(message, status, 'text/plain')


class LorisRequest(object):

    def __init__(self, request, redirect_id_slash_to_info=True, proxy_path=None):
        #make sure path is unquoted, so we know what we're working with
        self._path = unquote(request.path)
        self._request = request
        self._redirect_id_slash_to_info = redirect_id_slash_to_info
        self._proxy_path = proxy_path
        self._dissect_uri()

    @property
    def base_uri(self):
        if self._proxy_path is not None:
            uri = '%s%s' % (self._proxy_path, self.ident)
        elif self._request.script_root != '':
            uri = '%s%s' % (self._request.url_root, self.ident)
        else:
            uri = '%s%s' % (self._request.host_url, self.ident)
        return uri

    def _dissect_uri(self):
        self.ident = ''
        self.params = ''
        #handle some initial static views first
        if self._path == '/':
            self.request_type = 'index'
            return

        elif self._path[1:] == 'favicon.ico':
            self.request_type = 'favicon'
            return

        #check for image request
        #Note: this doesn't guarantee that all the parameters have valid
        #values - see regexes in constants.py.
        image_match = constants.IMAGE_RE.match(self._path)

        #check for info request
        info_match = constants.INFO_RE.match(self._path)

        #process image request
        if image_match:
            groups = image_match.groupdict()
            self.ident = quote_plus(groups['ident'])
            self.params = {'region': groups['region'],
                      'size': groups['size'],
                      'rotation': groups['rotation'],
                      'quality': groups['quality'],
                      'format': groups['format']}
            self.request_type = 'image'

        #process info request
        elif info_match:
            groups = info_match.groupdict()
            self.ident = quote_plus(groups['ident'])
            self.params = 'info.json'
            self.request_type = 'info'

        #if the request didn't match the stricter regexes above, but it does
        #match this one, we know we have an invalid image request, so we can
        #return a 400 BadRequest to the user.
        elif constants.LOOSER_IMAGE_RE.match(self._path):
            self.request_type = 'bad_image_request'

        else: #treat it as a redirect_info
            ident = self._path[1:]
            if ident.endswith('/') and self._redirect_id_slash_to_info:
                ident = ident[:-1]
            self.ident = quote_plus(ident)
            self.request_type = 'redirect_info'


class Loris(object):

    def __init__(self, app_configs={}):
        '''The WSGI Application.
        Args:
            app_configs ({}):
                A dictionary of dictionaries that represents the loris.conf
                file.
        '''
        self.app_configs = app_configs
        self.logger = configure_logging(app_configs['logging'])
        self.logger.debug('Loris initialized with these settings:')
        [self.logger.debug('%s.%s=%s', key, sub_key, self.app_configs[key][sub_key])
            for key in self.app_configs for sub_key in self.app_configs[key]]

        # make the loris.Loris configs attrs for easier access
        _loris_config = self.app_configs['loris.Loris']
        self.tmp_dp = _loris_config['tmp_dp']
        self.www_dp = _loris_config['www_dp']
        self.enable_caching = _loris_config['enable_caching']
        self.redirect_canonical_image_request = _loris_config['redirect_canonical_image_request']
        self.redirect_id_slash_to_info = _loris_config['redirect_id_slash_to_info']
        self.proxy_path = _loris_config.get('proxy_path', None)
        self.cors_regex = _loris_config.get('cors_regex', None)
        if self.cors_regex:
            self.cors_regex = re.compile(self.cors_regex)

        self.transformers = self._load_transformers()
        self.resolver = self._load_resolver()
        self.authorizer = self._load_authorizer()
        self.max_size_above_full = _loris_config.get('max_size_above_full', 200)

        if self.enable_caching:
            self.info_cache = InfoCache(self.app_configs['img_info.InfoCache']['cache_dp'])
            cache_dp = self.app_configs['img.ImageCache']['cache_dp']
            self.img_cache = img.ImageCache(cache_dp)

    def _load_transformers(self):
        tforms = self.app_configs['transforms']
        source_formats = [k for k in tforms if isinstance(tforms[k], dict)]
        self.logger.debug('Source formats: %r', source_formats)
        global_tranform_options = dict((k, v) for k, v in tforms.iteritems() if not isinstance(v, dict))
        self.logger.debug('Global transform options: %r', global_tranform_options)

        transformers = {}
        for sf in source_formats:
            # merge [transforms] options and [transforms][source_format]] options
            config = dict(list(self.app_configs['transforms'][sf].items()) + list(global_tranform_options.items()))
            transformers[sf] = self._load_transformer(config)
        return transformers

    def _load_transformer(self, config):
        Klass = getattr(transforms, config['impl'])
        instance = Klass(config)
        self.logger.debug('Loaded Transformer %s', config['impl'])
        return instance

    def _load_resolver(self):
        impl = self.app_configs['resolver']['impl']
        ResolverClass = self._import_class(impl)
        resolver_config =  self.app_configs['resolver']
        return ResolverClass(resolver_config)

    def _load_authorizer(self):
        try:
            impl = self.app_configs['authorizer']['impl']
        except:
            return None
        AuthorizerClass = self._import_class(impl)
        return AuthorizerClass(self.app_configs['authorizer'])

    def _import_class(self, qname):
        '''Imports a class AND returns it (the class, not an instance).
        '''
        module_name = '.'.join(qname.split('.')[:-1])
        class_name = qname.split('.')[-1]
        module = __import__(module_name, fromlist=[class_name])
        self.logger.debug('Imported %s', qname)
        return getattr(module, class_name)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.route(request)
        return response(environ, start_response)

    def route(self, request):
        loris_request = LorisRequest(request, self.redirect_id_slash_to_info, self.proxy_path)
        request_type = loris_request.request_type

        if request_type == 'index':
            return self.get_index(request)

        if request_type == 'favicon':
            return self.get_favicon(request)

        if request_type == 'bad_image_request':
            return BadRequestResponse()

        ident = loris_request.ident
        base_uri = loris_request.base_uri

        if request_type == 'redirect_info':
            if not self.resolver.is_resolvable(ident):
                msg = "could not resolve identifier: %s " % (ident)
                return NotFoundResponse(msg)

            r = LorisResponse()
            r.headers['Location'] = '%s/info.json' % (base_uri,)
            r.set_acao(request)
            r.status_code = 303
            return r

        elif request_type == 'info':

            if request.method == "OPTIONS":
                # never redirect
                r = LorisResponse()
                r.set_acao(request)
                r.status_code = 200
                return r

            return self.get_info(request, ident, base_uri)

        else: #request_type == 'image':
            params = loris_request.params
            fmt = params['format']
            if fmt not in self.app_configs['transforms']['target_formats']:
                return BadRequestResponse('"%s" is not a supported format' % (fmt,))
            quality = params['quality']
            rotation = params['rotation']
            size = params['size']
            region = params['region']

            return self.get_img(request, ident, region, size, rotation, quality, fmt, base_uri)

    def __call__(self, environ, start_response):
        '''
        This makes Loris executable.
        '''
        return self.wsgi_app(environ, start_response)

    def get_index(self, request):
        '''
        Just so there's something at /.
        '''
        f = open(path.join(self.www_dp, 'index.txt'), 'rb')
        r = Response(f, content_type='text/plain')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_favicon(self, request):
        f = path.join(self.www_dp, 'icons', 'loris-icon.png')
        r = Response(open(f, 'rb'), content_type='image/x-icon')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_info(self, request, ident, base_uri):
        try:
            info, last_mod = self._get_info(ident,request,base_uri)
        except ResolverException as re:
            return NotFoundResponse(str(re))
        except ImageInfoException as ie:
            return ServerSideErrorResponse(str(ie))
        except IOError as e:
            msg = '%s \n(This is likely a permissions problem)' % e
            return ServerSideErrorResponse(msg)

        r = LorisResponse()
        r.set_acao(request, self.cors_regex)
        ims_hdr = request.headers.get('If-Modified-Since')
        ims = parse_date(ims_hdr)
        last_mod = parse_date(http_date(last_mod)) # see note under get_img

        if self.authorizer and self.authorizer.is_protected(info):
            authed = self.authorizer.is_authorized(info, request)
            if authed['status'] == 'deny':
                r.status_code = 401
                # trash If-Mod-Since to ensure no 304
                ims = None
            elif authed['status'] == 'redirect':
                r.status_code = 302
                r.location = authed['location']
            # Otherwise we're okay

        if ims and ims >= last_mod:
            self.logger.debug('Sent 304 for %s ', ident)
            r.status_code = 304
        else:
            if last_mod:
                r.last_modified = last_mod
            callback = request.args.get('callback', None)
            if callback:
                r.mimetype = 'application/javascript'
                r.data = '%s(%s);' % (callback, info.to_iiif_json())
            else:
                if request.headers.get('accept') == 'application/ld+json':
                    r.content_type = 'application/ld+json'
                else:
                    r.content_type = 'application/json'
                    l = '<http://iiif.io/api/image/2/context.json>;rel="http://www.w3.org/ns/json-ld#context";type="application/ld+json"'
                    r.headers['Link'] = '%s,%s' % (r.headers['Link'], l)
                r.data = info.to_iiif_json()
        return r

    def _get_info(self,ident,request,base_uri):
        if self.enable_caching:
            in_cache = request in self.info_cache
        else:
            in_cache = False

        #Checking for src_format in ImageInfo signals that it's not old cache data:
        #   src_format didn't used to be in the Info cache, but now it is.
        #   If we don't see src_format, that means it's old cache data, so just
        #   ignore it and cache new ImageInfo.
        #   TODO: remove src_format check in Loris 4.0.
        if in_cache and self.info_cache[request][0].src_format:
            return self.info_cache[request]
        else:

            info = self.resolver.resolve(self, ident, base_uri)

            # Maybe inject services before caching
            if self.authorizer and self.authorizer.is_protected(info):
                # Call get_services to inject
                svcs = self.authorizer.get_services_info(info)
                if svcs and 'service' in svcs:
                    info.service = svcs['service']

            # store
            if self.enable_caching:
                self.logger.debug('ident used to store %s: %s', ident, ident)
                self.info_cache[request] = info
                # pick up the timestamp... :()
                info,last_mod = self.info_cache[request]
            else:
                last_mod = None

            return (info,last_mod)

    def _set_canonical_link(
        self, request, response, image_request, image_info
    ):
        if self.proxy_path:
            root = self.proxy_path
        else:
            root = request.url_root

        canonical_path = image_request.canonical_request_path(image_info)
        canonical_uri = '%s%s' % (root, canonical_path)
        response.headers['Link'] = '%s,<%s>;rel="canonical"' % (
            response.headers['Link'], canonical_uri
        )

    def get_img(self, request, ident, region, size, rotation, quality, target_fmt, base_uri):
        '''Get an Image.
        Args:
            request (Request):
                Forwarded by dispatch_request
            ident (str):
                The identifier portion of the IIIF URI syntax

        '''
        r = LorisResponse()
        r.set_acao(request, self.cors_regex)
        # ImageRequest's Parameter attributes, i.e. RegionParameter etc. are
        # decorated with @property and not constructed until they are first
        # accessed, which mean we don't have to catch any exceptions here.
        image_request = img.ImageRequest(ident, region, size, rotation,
                                         quality, target_fmt)

        self.logger.debug('Image Request Path: %s', image_request.request_path)

        if self.enable_caching:
            in_cache = image_request in self.img_cache
        else:
            in_cache = False

        try:
            # We need the info to check authorization,
            # ... still cheaper than always resolving as likely to be cached
            info = self._get_info(ident, request, base_uri)[0]
        except ResolverException as re:
            return NotFoundResponse(str(re))

        if self.authorizer and self.authorizer.is_protected(info):
            authed = self.authorizer.is_authorized(info, request)

            if authed['status'] != 'ok':
                # Images don't redirect, they just deny out
                r.status_code = 401
                return r

        if in_cache:
            fp, img_last_mod = self.img_cache[image_request]
            ims_hdr = request.headers.get('If-Modified-Since')
            # The stamp from the FS needs to be rounded using the same precision
            # as when went sent it, so for an accurate comparison turn it into
            # an http date and then parse it again :-( :
            img_last_mod = parse_date(http_date(img_last_mod))
            self.logger.debug("Time from FS (default, rounded): %s", img_last_mod)
            self.logger.debug("Time from IMS Header (parsed): %s", parse_date(ims_hdr))
            # ims_hdr = parse_date(ims_hdr) # catch parsing errors?
            if ims_hdr and parse_date(ims_hdr) >= img_last_mod:
                self.logger.debug('Sent 304 for %s ', fp)
                r.status_code = 304
                return r
            else:
                r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
                r.status_code = 200
                r.last_modified = img_last_mod
                r.headers['Content-Length'] = path.getsize(fp)
                r.response = open(fp, 'rb')

                # hand the Image object its info
                info = self._get_info(ident, request, base_uri)[0]

                self._set_canonical_link(
                    request=request,
                    response=r,
                    image_request=image_request,
                    image_info=info
                )
                return r
        else:
            try:
                # 1. Get the info
                info = self._get_info(ident, request, base_uri)[0]

                # 2. Check that we can make the quality requested
                if image_request.quality not in info.profile.description['qualities']:
                    return BadRequestResponse('"%s" quality is not available for this image' % (image_request.quality,))

                # 3. Check if requested size is allowed
                if image_request.request_resolution_too_large(
                    max_size_above_full=self.max_size_above_full,
                    image_info=info
                ):
                    return NotFoundResponse('Resolution not available')

                # 4. Redirect if appropriate
                if self.redirect_canonical_image_request:
                    if not image_request.is_canonical(info):
                        self.logger.debug('Attempting redirect to %s', image_request.canonical_request_path,)
                        r.headers['Location'] = image_request.canonical_request_path
                        r.status_code = 301
                        return r

                # 5. Make an image
                fp = self._make_image(
                    image_request=image_request,
                    image_info=info
                )

            except ResolverException as re:
                return NotFoundResponse(str(re))
            except TransformException as te:
                return ServerSideErrorResponse(te)
            except (RequestException, SyntaxException) as e:
                return BadRequestResponse(str(e))
            except ImageInfoException as ie:
                # 500s!
                # ImageInfoException is only raised when
                # ImageInfo.from_image_file() can't  determine the format of the
                # source image. It results in a 500, but isn't necessarily a
                # developer error.
                return ServerSideErrorResponse(ie)
            except (CalledProcessError,IOError) as e:
                # CalledProcessError and IOError typically happen when there are
                # permissions problems with one of the files or directories
                # used by the transformer.
                msg = '''%s \n\nThis is likely a permissions problem, though it\'s
possible that there was a problem with the source file
(%s).''' % (str(e),info.src_img_fp)
                return ServerSideErrorResponse(msg)
        r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
        r.status_code = 200
        r.last_modified = datetime.utcfromtimestamp(path.getctime(fp))
        r.headers['Content-Length'] = path.getsize(fp)
        self._set_canonical_link(
            request=request,
            response=r,
            image_request=image_request,
            image_info=info
        )
        r.response = open(fp, 'rb')

        if not self.enable_caching:
            r.call_on_close(lambda: unlink(fp))

        return r

    def _make_image(self, image_request, image_info):
        """Call the appropriate transformer to create the image.

        Args:
            image_request (ImageRequest)
            image_info (ImageInfo)
        Returns:
            (str) the file path of the new image

        """
        temp_file = NamedTemporaryFile(
            dir=self.tmp_dp,
            suffix='.%s' % image_request.format,
            delete=False
        )
        temp_fp = temp_file.name

        transformer = self.transformers[image_info.src_format]
        transformer.transform(
            target_fp=temp_fp,
            image_request=image_request,
            image_info=image_info
        )

        if self.enable_caching:
            temp_fp = self.img_cache.upsert(
                image_request=image_request,
                temp_fp=temp_fp,
                image_info=image_info
            )
            # TODO: not sure how the non-canonical use case works
            self.img_cache.store(
                image_request=image_request,
                image_info=image_info,
                canonical_fp=temp_fp
            )

        return temp_fp


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    import sys

    project_dp = path.dirname(path.dirname(path.realpath(__file__)))

    sys.path.append(path.join(project_dp)) # to find any local resolvers

    app = create_app(debug=True) # or 'opj'

    run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True)
    # To debug ssl:
    # run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True,
    #     ssl_context='adhoc')
