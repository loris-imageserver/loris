#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
webapp.py
=========
Implements IIIF 2.0 <http://iiif.io/api/image/2.0/> level 2
'''
# from ConfigParser import RawConfigParser
from configobj import ConfigObj
from datetime import datetime
from decimal import getcontext
from img_info import ImageInfo
from img_info import ImageInfoException
from img_info import InfoCache
from logging.handlers import RotatingFileHandler
from loris_exception import LorisException
from loris_exception import RequestException
from loris_exception import SyntaxException
from loris_exception import ImageException
from loris_exception import ResolverException
from loris_exception import TransformException
from os import path, makedirs, unlink, removedirs, symlink
from subprocess import CalledProcessError
from urllib import unquote, quote_plus
from werkzeug.http import parse_date, parse_accept_header, http_date
from werkzeug.wrappers import Request, Response, BaseResponse, CommonResponseDescriptorsMixin
import constants
import img
import logging
import random
import re
import string
import transforms
import os

getcontext().prec = 25 # Decimal precision. This should be plenty.

def create_app(debug=False, debug_jp2_transformer='kdu', config_file_path=''):
    if debug:
        # change a few things, read the config and set up logging
        project_dp = path.dirname(path.dirname(path.realpath(__file__)))
        config_file_path = path.join(project_dp, 'etc', 'loris2.conf')

        config = read_config(config_file_path)

        config['logging']['log_to'] = 'console'
        config['logging']['log_level'] = 'DEBUG'
        logger = __configure_logging(config['logging'])
        logger.debug('Running in debug mode.')

        # override some stuff to look at relative or tmp directories.
        config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
        config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
        config['loris.Loris']['enable_caching'] = True
        config['img.ImageCache']['cache_dp'] = '/tmp/loris/cache/img'
        config['img_info.InfoCache']['cache_dp'] = '/tmp/loris/cache/info'
        config['resolver']['impl'] = 'loris.resolver.SimpleFSResolver'
        config['resolver']['src_img_root'] = path.join(project_dp,'tests','img')

        if debug_jp2_transformer == 'opj':
            from transforms import OPJ_JP2Transformer
            opj_decompress = OPJ_JP2Transformer.local_opj_decompress_path()
            config['transforms']['jp2']['opj_decompress'] = path.join(project_dp, opj_decompress)
            libopenjp2_dir = OPJ_JP2Transformer.local_libopenjp2_dir()
            config['transforms']['jp2']['opj_libs'] = path.join(project_dp, libopenjp2_dir)
        else: # kdu
            from transforms import KakaduJP2Transformer
            kdu_expand = KakaduJP2Transformer.local_kdu_expand_path()
            config['transforms']['jp2']['kdu_expand'] = path.join(project_dp, kdu_expand)
            libkdu_dir = KakaduJP2Transformer.local_libkdu_dir()
            config['transforms']['jp2']['kdu_libs'] = path.join(project_dp, libkdu_dir)

    else:
        config = read_config(config_file_path)
        logger = __configure_logging(config['logging'])

    # Make any dirs we may need
    dirs_to_make = []
    try:
        dirs_to_make.append(config['loris.Loris']['tmp_dp'])
        if config['logging']['log_to'] == 'file':
            dirs_to_make.append(config['logging']['log_dir'])
        if config['loris.Loris']['enable_caching']:
            dirs_to_make.append(config['img.ImageCache']['cache_dp'])
            dirs_to_make.append(config['img_info.InfoCache']['cache_dp'])
        [makedirs(d) for d in dirs_to_make if not path.exists(d)]
    except OSError as ose:
        from sys import exit
        from os import strerror
        # presumably it's permissions
        msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
        logger.fatal(msg)
        logger.fatal('Exiting')
        exit(77)
    else:
        return Loris(logger, config)

def read_config(config_file_path):
    config = ConfigObj(config_file_path, unrepr=True, interpolation='template')
    # add the OS environment variables as the DEFAULT section to support
    # interpolating their values into other keys
    # make a copy of the os.environ dictionary so that the config object can't
    # inadvertently modify the environment
    config['DEFAULT'] = dict(os.environ)
    return config

def __configure_logging(config):
    logger = logging.getLogger()

    conf_level = config['log_level']

    if conf_level == 'CRITICAL': logger.setLevel(logging.CRITICAL)
    elif conf_level == 'ERROR': logger.setLevel(logging.ERROR)
    elif conf_level == 'WARNING': logger.setLevel(logging.WARNING)
    elif conf_level == 'INFO': logger.setLevel(logging.INFO)
    else: logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt=config['format'])

    if config['log_to'] == 'file':
        if not getattr(logger, 'handler_set', None):
            fp = '%s.log' % (path.join(config['log_dir'], 'loris'),)
            handler = RotatingFileHandler(fp,
                maxBytes=config['max_size'],
                backupCount=config['max_backups'],
                delay=True)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    else:
        if not getattr(logger, 'handler_set', None):
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

    def __init__(self, request, redirect_id_slash_to_info, proxy_path):
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
        #Note: this doesn't guarantee that all the parameters have valid values - see regexes in constants.py.
        image_match = constants.IMAGE_RE.match(self._path)
        if image_match:
            groups = image_match.groupdict()
            self.ident = quote_plus(groups['ident'])
            self.params = {'region': groups['region'],
                      'size': groups['size'],
                      'rotation': groups['rotation'],
                      'quality': groups['quality'],
                      'format': groups['format']}
            self.request_type = 'image'

        #check for info request
        elif self._path.endswith('info.json'):
            ident = '/'.join(self._path[1:].split('/')[:-1])
            self.ident = quote_plus(ident)
            self.params = 'info.json'
            self.request_type = 'info'

        #if the request didn't match the stricter regex above, but it does match this one, we know we have an
        # invalid image request, so we can return a 400 BadRequest to the user.
        elif constants.LOOSER_IMAGE_RE.match(self._path):
            self.request_type = 'bad_image_request'

        else: #treat it as a redirect_info
            ident = self._path[1:]
            if ident.endswith('/') and self._redirect_id_slash_to_info:
                ident = ident[:-1]
            self.ident = quote_plus(ident)
            self.request_type = 'redirect_info'


class Loris(object):

    def __init__(self, logger, app_configs={}):
        '''The WSGI Application.
        Args:
            config ({}):
                A dictionary of dictionaries that represents the loris.conf
                file.
            debug (bool)
        '''
        self.app_configs = app_configs
        self.logger = logger
        self.logger.debug('Loris initialized with these settings:')
        [self.logger.debug('%s.%s=%s' % (key, sub_key, self.app_configs[key][sub_key]))
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
        self.max_size_above_full = _loris_config.get('max_size_above_full', 200)

        if self.enable_caching:
            self.info_cache = InfoCache(self.app_configs['img_info.InfoCache']['cache_dp'])
            cache_dp = self.app_configs['img.ImageCache']['cache_dp']
            self.img_cache = img.ImageCache(cache_dp)

    def _load_transformers(self):
        tforms = self.app_configs['transforms']
        source_formats = [k for k in tforms if isinstance(tforms[k], dict)]
        self.logger.debug('Source formats: %s' % (repr(source_formats),))
        global_tranform_options = dict((k, v) for k, v in tforms.iteritems() if not isinstance(v, dict))
        self.logger.debug('Global transform options: %s' % (repr(global_tranform_options),))

        transformers = {}
        for sf in source_formats:
            # merge [transforms] options and [transforms][source_format]] options
            config = dict(self.app_configs['transforms'][sf].items() + global_tranform_options.items())
            transformers[sf] = self._load_transformer(config)
        return transformers

    def _load_transformer(self, config):
        Klass = getattr(transforms, config['impl'])
        instance = Klass(config)
        self.logger.debug('Loaded Transformer %s' % (config['impl'],))
        return instance

    def _load_resolver(self):
        impl = self.app_configs['resolver']['impl']
        ResolverClass = self._import_class(impl)
        resolver_config =  self.app_configs['resolver']
        return ResolverClass(resolver_config)

    def _import_class(self, qname):
        '''Imports a class AND returns it (the class, not an instance).
        '''
        module_name = '.'.join(qname.split('.')[:-1])
        class_name = qname.split('.')[-1]
        module = __import__(module_name, fromlist=[class_name])
        self.logger.debug('Imported %s' % (qname,))
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
        f = file(path.join(self.www_dp, 'index.txt'))
        r = Response(f, content_type='text/plain')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_favicon(self, request):
        f = path.join(self.www_dp, 'icons', 'loris-icon.png')
        r = Response(file(f), content_type='image/x-icon')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_info(self, request, ident, base_uri):
        try:
            info, last_mod = self._get_info(ident,request,base_uri)
        except ResolverException as re:
            return NotFoundResponse(re.message)
        except ImageInfoException as ie:
            return ServerSideErrorResponse(ie.message)
        except IOError as e:
            msg = '%s \n(This is likely a permissions problem)' % e
            return ServerSideErrorResponse(msg)

        r = LorisResponse()
        r.set_acao(request, self.cors_regex)
        ims_hdr = request.headers.get('If-Modified-Since')

        ims = parse_date(ims_hdr)
        last_mod = parse_date(http_date(last_mod)) # see note under get_img

        if ims and ims >= last_mod:
            self.logger.debug('Sent 304 for %s ' % (ident,))
            r.status_code = 304
        else:
            if last_mod:
                r.last_modified = last_mod
            callback = request.args.get('callback', None)
            if callback:
                r.mimetype = 'application/javascript'
                r.data = '%s(%s);' % (callback, info.to_json())
            else:
                if request.headers.get('accept') == 'application/ld+json':
                    r.content_type = 'application/ld+json'
                else:
                    r.content_type = 'application/json'
                    l = '<http://iiif.io/api/image/2/context.json>;rel="http://www.w3.org/ns/json-ld#context";type="application/ld+json"'
                    r.headers['Link'] = '%s,%s' % (r.headers['Link'], l)
                r.data = info.to_json()
        return r

    def _get_info(self,ident,request,base_uri,src_fp=None,src_format=None):
        if self.enable_caching:
            in_cache = request in self.info_cache
        else:
            in_cache = False

        if in_cache:
            return self.info_cache[request]
        else:
            if not all((src_fp, src_format)):
                # get_img can pass in src_fp, src_format because it needs them
                # elsewhere; get_info does not.
                src_fp, src_format = self.resolver.resolve(ident)

            try:
                formats = self.transformers[src_format].target_formats
            except KeyError:
                raise ImageInfoException(500, 'unknown source format')

            self.logger.debug('Format: %s' % (src_format,))
            self.logger.debug('File Path: %s' % (src_fp,))
            self.logger.debug('Identifier: %s' % (ident,))
            self.logger.debug('Base URI: %s' % (base_uri,))

            # get the info
            info = ImageInfo.from_image_file(base_uri, src_fp, src_format, formats, self.max_size_above_full)

            # store
            if self.enable_caching:
                self.logger.debug('ident used to store %s: %s' % (ident,ident))
                self.info_cache[request] = info
                # pick up the timestamp... :()
                info,last_mod = self.info_cache[request]
            else:
                last_mod = None

            return (info,last_mod)


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

        self.logger.debug('Image Request Path: %s' % (image_request.request_path,))

        if self.enable_caching:
            in_cache = image_request in self.img_cache
        else:
            in_cache = False

        if in_cache:
            fp, img_last_mod = self.img_cache[image_request]
            ims_hdr = request.headers.get('If-Modified-Since')
            # The stamp from the FS needs to be rounded using the same precision
            # as when went sent it, so for an accurate comparison turn it into
            # an http date and then parse it again :-( :
            img_last_mod = parse_date(http_date(img_last_mod))
            self.logger.debug("Time from FS (default, rounded): " + str(img_last_mod))
            self.logger.debug("Time from IMS Header (parsed): " + str(parse_date(ims_hdr)))
            # ims_hdr = parse_date(ims_hdr) # catch parsing errors?
            if ims_hdr and parse_date(ims_hdr) >= img_last_mod:
                self.logger.debug('Sent 304 for %s ' % (fp,))
                r.status_code = 304
                return r
            else:
                r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
                r.status_code = 200
                r.last_modified = img_last_mod
                r.headers['Content-Length'] = path.getsize(fp)
                r.response = file(fp)

                # resolve the identifier
                src_fp, src_format = self.resolver.resolve(ident)
                # hand the Image object its info
                info = self._get_info(ident, request, base_uri, src_fp, src_format)[0]
                image_request.info = info
                # we need to do the above to set the canonical link header

                canonical_uri = '%s%s' % (request.url_root, image_request.canonical_request_path)
                r.headers['Link'] = '%s,<%s>;rel="canonical"' % (r.headers['Link'], canonical_uri,)
                return r
        else:
            try:

                # 1. Resolve the identifier
                src_fp, src_format = self.resolver.resolve(ident)

                # 2. Hand the Image object its info
                info = self._get_info(ident, request, base_uri, src_fp, src_format)[0]
                image_request.info = info

                # 3. Check that we can make the quality requested
                if image_request.quality not in info.profile[1]['qualities']:
                    return BadRequestResponse('"%s" quality is not available for this image' % (image_request.quality,))

                # 4. Check if requested size is allowed
                if image_request.request_resolution_too_large(self.max_size_above_full):
                    return NotFoundResponse('Resolution not available')

                # 5. Redirect if appropriate
                if self.redirect_canonical_image_request:
                    if not image_request.is_canonical:
                        self.logger.debug('Attempting redirect to %s' % (image_request.canonical_request_path,))
                        r.headers['Location'] = image_request.canonical_request_path
                        r.status_code = 301
                        return r

                # 6. Make an image
                fp = self._make_image(image_request, src_fp, src_format)

            except ResolverException as re:
                return NotFoundResponse(re.message)
            except TransformException as te:
                return ServerSideErrorResponse(te)
            except (RequestException, SyntaxException) as e:
                return BadRequestResponse(e.message)
            except (ImageException,ImageInfoException) as ie:
                # 500s!
                # ImageException is only raised in when ImageRequest.info
                # isn't set and is a developer error. It should never happen!
                #
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
(%s).''' % (str(e),src_fp)
                return ServerSideErrorResponse(msg)
        r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
        r.status_code = 200
        r.last_modified = datetime.utcfromtimestamp(path.getctime(fp))
        r.headers['Content-Length'] = path.getsize(fp)
        canonical_uri = '%s%s' % (request.url_root, image_request.canonical_request_path)
        r.headers['Link'] = '%s,<%s>;rel="canonical"' % (r.headers['Link'], canonical_uri,)
        r.response = file(fp)

        if not self.enable_caching:
            r.call_on_close(unlink(fp))

        return r

    def _make_image(self, image_request, src_fp, src_format):
        '''
        Args:
            image_request (img.ImageRequest)
            src_fp (str)
            src_format (str)
        Returns:
            (str) the fp of the new image
        '''
        # figure out paths, make dirs
        if self.enable_caching:
            target_fp = self.img_cache.create_dir_and_return_file_path(image_request)
        else:
            # random str
            n = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
            target_fp = '%s.%s' % (path.join(self.tmp_dp, n), image_request.format)

        transformer = self.transformers[src_format]

        transformer.transform(src_fp, target_fp, image_request)
        if self.enable_caching:
            self.img_cache[image_request] = target_fp
        return target_fp


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    import sys
    extra_files = []

    project_dp = path.dirname(path.dirname(path.realpath(__file__)))
    conf_fp = path.join(project_dp, 'etc', 'loris2.conf')
    extra_files.append(conf_fp)

    sys.path.append(path.join(project_dp)) # to find any local resolvers

    app = create_app(debug=True) # or 'opj'

    run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True,
        extra_files=extra_files)
    # To debug ssl:
    # run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True,
    #     extra_files=extra_files, ssl_context='adhoc')
