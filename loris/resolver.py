# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from logging import getLogger
from loris_exception import ResolverException
from os.path import join, exists, isfile
from os import makedirs
from os.path import dirname
from shutil import copy
from urllib import unquote, quote_plus

import constants
import hashlib
import glob
import requests

logger = getLogger(__name__)

class _AbstractResolver(object):
    def __init__(self, config):
        self.config = config

    def is_resolvable(self, ident):
        """
        The idea here is that in some scenarios it may be cheaper to check 
        that an id is resolvable than to actually resolve it. For example, for 
        an HTTP resolver, this could be a HEAD instead of a GET.

        Args:
            ident (str):
                The identifier for the image.
        Returns:
            bool
        """
        cn = self.__class__.__name__
        raise NotImplementedError('is_resolvable() not implemented for %s' % (cn,))

    def resolve(self, ident):
        """
        Given the identifier of an image, get the path (fp) and format (one of. 
        'jpg', 'tif', or 'jp2'). This will likely need to be reimplemented for
        environments and can be as smart or dumb as you want.
        
        Args:
            ident (str):
                The identifier for the image.
        Returns:
            (str, str): (fp, format)
        Raises:
            ResolverException when something goes wrong...
        """
        cn = self.__class__.__name__
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))


class SimpleFSResolver(_AbstractResolver):

    def __init__(self, config):
        super(SimpleFSResolver, self).__init__(config)
        self.cache_root = self.config['src_img_root']

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        return exists(fp)

    @staticmethod
    def _format_from_ident(ident):
        return ident.split('.')[-1]

    def resolve(self, ident):
        # For this dumb version a constant path is prepended to the identfier 
        # supplied to get the path It assumes this 'identifier' ends with a file 
        # extension from which the format is then derived.
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        logger.debug('src image: %s' % (fp,))

        if not exists(fp):
            public_message = 'Source image not found for identifier: %s.' % (ident,)
            log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
            logger.warn(log_message)
            raise ResolverException(404, public_message)

        format = SimpleFSResolver._format_from_ident(ident)
        logger.debug('src format %s' % (format,))

        return (fp, format)

class SimpleHTTPResolver(_AbstractResolver):
    '''
    Example resolver that one might use if image files were coming from
    an http image store (like Fedora Commons). The first call to `resolve()`
    copies the source image into a local cache; subsequent calls use local
    copy from the cache.

    The config dictionary MUST contain
     * `cache_root`, which is the absolute path to the directory where source images
        should be cached.

    The config dictionary MAY contain
     * `source_prefix`, the url up to the identifier.
     * `source_suffix`, the url after the identifier (if applicable).
     * `default_format`, the format of images (will use content-type of response if not specified).
     * `head_resolvable` with value True, whether to make HEAD requests to verify object existence (don't set if using
        Fedora Commons prior to 3.8).
     * `uri_resolvable` with value True, allows one to use full uri's to resolve to an image.
     * `user`, the username to make the HTTP request as.
     * `pw`, the password to make the HTTP request as.
    '''
    def __init__(self, config):
        super(SimpleHTTPResolver, self).__init__(config)

        self.source_prefix = self.config.get('source_prefix', '')

        self.source_suffix = self.config.get('source_suffix', '')

        self.default_format = self.config.get('default_format', None)

        self.head_resolvable = self.config.get('head_resolvable', False)

        self.uri_resolvable = self.config.get('uri_resolvable', False)

        self.user = self.config.get('user', None)

        self.pw = self.config.get('pw', None)

        if 'cache_root' in self.config:
            self.cache_root = self.config['cache_root']
        else:
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Missing setting for cache_root.'
            logger.error(message)
            raise ResolverException(500, message)

        if not self.uri_resolvable and self.source_prefix == '':
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Must either set uri_resolvable' \
                      ' or source_prefix settings.'
            logger.error(message)
            raise ResolverException(500, message)

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.cache_root, SimpleHTTPResolver._cache_subroot(ident))
        if exists(fp):
            return True
        else:
            fp = SimpleHTTPResolver._web_request_url(ident, self.uri_resolvable, self.source_prefix, self.source_suffix)

            if self.head_resolvable:
                try:
                    if self.user is not None and self.pw is not None:
                        response = requests.head(fp, auth=(self.user, self.pw))
                    else:
                        response = requests.head(fp)
                except requests.exceptions.MissingSchema:
                    return False
            else:
                try:
                    if self.user is not None and self.pw is not None:
                        response = requests.get(fp, stream = True, auth=(self.user, self.pw))
                    else:
                        response = requests.get(fp, stream = True)
                except requests.exceptions.MissingSchema:
                    return False

            if response.status_code is 200:
                return True

        return False

    def format_from_ident(self, ident, potential_format):
        if self.default_format is not None:
            return self.default_format
        elif potential_format is not None:
            return potential_format
        elif ident.rfind('.') != -1 and (len(ident) - ident.rfind('.') <= 5):
            return ident.split('.')[-1]
        else:
            public_message = 'Format could not be determined for: %s.' % (ident,)
            log_message = 'Format could not be determined for: %s.' % (ident)
            logger.warn(log_message)
            raise ResolverException(404, public_message)

    @staticmethod
    def _web_request_url(ident, is_uri_resolvable, prefix, suffix):
        if (ident[0:6] == 'http:/' or ident[0:7] == 'https:/') and is_uri_resolvable:
            #ident is http request with no prefix or suffix specified
            #For some reason, identifier is http:/<url> or https:/<url>? Hack to correct.
            return ident[0:ident.find('/')] + '/' + ident[ident.find('/'):len(ident)]
        else:
            return prefix + ident + suffix

    #Get a subdirectory structure for the cache_subroot through hashing.
    @staticmethod
    def _cache_subroot(ident):
        cache_subroot = ''

        #Split out potential pidspaces... Fedora Commons most likely use case.
        if ident[0:6] != 'http:/' and ident[0:7] != 'https:/' and len(ident.split(':')) > 1:
            for split_ident in ident.split(':')[0:-1]:
                cache_subroot = join(cache_subroot, split_ident)
        elif ident[0:6] == 'http:/' or ident[0:7] == 'https:/':
            cache_subroot = 'http'

        cache_subroot = join(cache_subroot, SimpleHTTPResolver._ident_file_structure(ident))

        return cache_subroot

    #Get the directory structure of the identifier itself
    @staticmethod
    def _ident_file_structure(ident):
        file_structure = ''
        ident_hash = hashlib.md5(quote_plus(ident)).hexdigest()
        #First level 2 digit directory then do three digits...
        file_structure_list = [ident_hash[0:2]] + [ident_hash[i:i+3] for i in range(2, len(ident_hash), 3)]

        for piece in file_structure_list:
            file_structure = join(file_structure, piece)

        return file_structure

    def resolve(self, ident):
        ident = unquote(ident)

        local_fp = join(self.cache_root, SimpleHTTPResolver._cache_subroot(ident))
        local_fp = join(local_fp)

        if exists(local_fp):
            cached_object = glob.glob(join(local_fp, 'loris_cache.*'))

            if len(cached_object) > 0:
                cached_object = cached_object[0]
            else:
                public_message = 'Cached image not found for identifier: %s.' % (ident)
                log_message = 'Cached image not found for identifier: %s. Empty directory where image expected?' % (ident)
                logger.warn(log_message)
                raise ResolverException(404, public_message)

            format = self.format_from_ident(cached_object,None)
            logger.debug('src image from local disk: %s' % (cached_object,))
            return (cached_object, format)
        else:
            fp = SimpleHTTPResolver._web_request_url(ident, self.uri_resolvable, self.source_prefix, self.source_suffix)

            logger.debug('src image: %s' % (fp,))

            try:
                if self.user is not None and self.pw is not None:
                    response = requests.get(fp, stream = True, auth=(self.user, self.pw))
                else:
                    response = requests.get(fp, stream = True)
            except requests.exceptions.MissingSchema:
                public_message = 'Bad URL request made for identifier: %s.' % (ident,)
                log_message = 'Bad URL request at %s for identifier: %s.' % (fp,ident)
                logger.warn(log_message)
                raise ResolverException(404, public_message)

            if response.status_code != 200:
                public_message = 'Source image not found for identifier: %s. Status code returned: %s' % (ident,response.status_code)
                log_message = 'Source image not found at %s for identifier: %s. Status code returned: %s' % (fp,ident,response.status_code)
                logger.warn(log_message)
                raise ResolverException(404, public_message)

            if 'content-type' in response.headers:
                try:
                    format = self.format_from_ident(ident, constants.FORMATS_BY_MEDIA_TYPE[response.headers['content-type']])
                except KeyError:
                    logger.warn('Your server may be responding with incorrect content-types. Reported %s for ident %s.'
                                % (response.headers['content-type'],ident))
                    #Attempt without the content-type
                    format = self.format_from_ident(ident, None)
            else:
                format = self.format_from_ident(ident, None)

            logger.debug('src format %s' % (format,))

            local_fp = join(local_fp, "loris_cache." + format)

            try:
                makedirs(dirname(local_fp))
            except:
                logger.debug("Directory already existed... possible problem if not a different format")

            with open(local_fp, 'wb') as fd:
                for chunk in response.iter_content(2048):
                    fd.write(chunk)

            logger.info("Copied %s to %s" % (fp, local_fp))

            return (local_fp, format)

class SourceImageCachingResolver(_AbstractResolver):
    '''
    Example resolver that one might use if image files were coming from
    mounted network storage. The first call to `resolve()` copies the source
    image into a local cache; subsequent calls use local copy from the cache.
 
    The config dictionary MUST contain 
     * `cache_root`, which is the absolute path to the directory where images 
        should be cached.
     * `source_root`, the root directory for source images.
    '''
    def __init__(self, config):
        super(SourceImageCachingResolver, self).__init__(config)
        self.cache_root = self.config['cache_root']
        self.source_root = self.config['source_root']

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.source_root, ident)
        return exists(fp)

    @staticmethod
    def _format_from_ident(ident):
        return ident.split('.')[-1]

    def resolve(self, ident):
        ident = unquote(ident)
        local_fp = join(self.cache_root, ident)

        if exists(local_fp):
            format = SourceImageCachingResolver._format_from_ident(ident)
            logger.debug('src image from local disk: %s' % (local_fp,))
            return (local_fp, format)
        else:
            fp = join(self.source_root, ident)
            logger.debug('src image: %s' % (fp,))
            if not exists(fp):
                public_message = 'Source image not found for identifier: %s.' % (ident,)
                log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
                logger.warn(log_message)
                raise ResolverException(404, public_message)

            makedirs(dirname(local_fp))
            copy(fp, local_fp)
            logger.info("Copied %s to %s" % (fp, local_fp))

            format = SourceImageCachingResolver._format_from_ident(ident)
            logger.debug('src format %s' % (format,))

            return (local_fp, format)




