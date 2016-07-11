# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from logging import getLogger
from loris_exception import ResolverException
from os.path import join, exists
from os import makedirs
from os.path import dirname
from shutil import copy
from urllib import unquote, quote_plus
from contextlib import closing

import constants
import hashlib
import glob
import requests
import re

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
    """
    For this dumb version a constant path is prepended to the identfier
    supplied to get the path It assumes this 'identifier' ends with a file
    extension from which the format is then derived.
    """

    def __init__(self, config):
        super(SimpleFSResolver, self).__init__(config)
        if 'src_img_roots' in self.config:
            self.source_roots = self.config['src_img_roots']
        else:
            self.source_roots = [self.config['src_img_root']]

    def raise_404_for_ident(self, ident):
        message = 'Source image not found for identifier: %s.' % (ident,)
        logger.warn(message)
        raise ResolverException(404, message)

    def source_file_path(self, ident):
        ident = unquote(ident)
        for directory in self.source_roots:
            fp = join(directory, ident)
            if exists(fp):
                return fp

    def is_resolvable(self, ident):
        return not self.source_file_path(ident) is None

    def format_from_ident(self, ident):
        return ident.split('.')[-1]

    def resolve(self, ident):

        if not self.is_resolvable(ident):
            self.raise_404_for_ident(ident)

        source_fp = self.source_file_path(ident)
        logger.debug('src image: %s' % (source_fp,))

        format = self.format_from_ident(ident)
        logger.debug('src format %s' % (format,))

        return (source_fp, format)


# To use this the resolver stanza of the config will have to have both the
# src_img_root as required by the SimpleFSResolver and also an
# [[extension_map]], which will be a hash mapping found extensions to the
# extensions that loris wants to see, e.g.
#
# [resolver]
# impl = 'loris.resolver.ExtensionNormalizingFSResolver'
# src_img_root = '/cnfs-ro/iiif/production/medusa-root' # r--
#   [[extension_map]]
#   jpeg = 'jpg'
#   tiff = 'tif'
# Note that case normalization happens before looking up in the extension_map.
class ExtensionNormalizingFSResolver(SimpleFSResolver):
    def __init__(self, config):
        super(ExtensionNormalizingFSResolver, self).__init__(config)
        self.extension_map = self.config['extension_map']

    def format_from_ident(self, ident):
        format = super(ExtensionNormalizingFSResolver, self).format_from_ident(ident)
        format = format.lower()
        format = self.extension_map.get(format, format)
        return format


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

        self.ssl_check = self.config.get('ssl_check', True)

        self.ident_regex = self.config.get('ident_regex', False)

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

    def request_options(self):
        # parameters to pass to all head and get requests;
        # currently only authorization, if configured
        if self.user is not None and self.pw is not None:
            return {'auth': (self.user, self.pw)}
        return {}

    def is_resolvable(self, ident):
        ident = unquote(ident)

        if self.ident_regex:
            regex = re.compile(self.ident_regex)
            if not regex.match(ident):
                return False

        fp = join(self.cache_root, SimpleHTTPResolver._cache_subroot(ident))
        if exists(fp):
            return True
        else:
            fp = self._web_request_url(ident)

            if self.head_resolvable:
                try:
                    with closing(requests.head(fp, verify=self.ssl_check, **self.request_options())) as response:
                        if response.status_code is 200:
                            return True
                except requests.exceptions.MissingSchema:
                    return False

            else:
                try:
                    with closing(requests.get(fp, stream=True, verify=self.ssl_check, **self.request_options())) as response:
                        if response.status_code is 200:
                            return True
                except requests.exceptions.MissingSchema:
                    return False

        return False

    def format_from_ident(self, ident, potential_format):
        if self.default_format is not None:
            return self.default_format
        elif potential_format is not None:
            return potential_format
        elif ident.rfind('.') != -1 and (len(ident) - ident.rfind('.') <= 5):
            return ident.split('.')[-1]
        else:
            message = 'Format could not be determined for: %s.' % (ident)
            logger.warn(message)
            raise ResolverException(404, message)

    def _web_request_url(self, ident):
        if (ident[0:6] == 'http:/' or ident[0:7] == 'https:/') and self.uri_resolvable:
            # ident is http request with no prefix or suffix specified
            # For some reason, identifier is http:/<url> or https:/<url>?
            # Hack to correct without breaking valid urls.
            first_slash = ident.find('/')
            return '%s//%s' % (ident[:first_slash], ident[first_slash:].lstrip('/'))
        else:
            return self.source_prefix + ident + self.source_suffix

    # Get a subdirectory structure for the cache_subroot through hashing.
    @staticmethod
    def _cache_subroot(ident):
        cache_subroot = ''

        # Split out potential pidspaces... Fedora Commons most likely use case.
        if ident[0:6] != 'http:/' and ident[0:7] != 'https:/' and len(ident.split(':')) > 1:
            for split_ident in ident.split(':')[0:-1]:
                cache_subroot = join(cache_subroot, split_ident)
        elif ident[0:6] == 'http:/' or ident[0:7] == 'https:/':
            cache_subroot = 'http'

        cache_subroot = join(cache_subroot, SimpleHTTPResolver._ident_file_structure(ident))

        return cache_subroot

    # Get the directory structure of the identifier itself
    @staticmethod
    def _ident_file_structure(ident):
        file_structure = ''
        ident_hash = hashlib.md5(quote_plus(ident)).hexdigest()
        # First level 2 digit directory then do three digits...
        file_structure_list = [ident_hash[0:2]] + [ident_hash[i:i+3] for i in range(2, len(ident_hash), 3)]

        for piece in file_structure_list:
            file_structure = join(file_structure, piece)

        return file_structure

    def cache_dir_path(self, ident):
        ident = unquote(ident)
        return join(
                self.cache_root,
                SimpleHTTPResolver._cache_subroot(ident)
        )

    def cache_file_path(self, ident):
        pass

    def raise_404_for_ident(self, ident):
        message = 'Image not found for identifier: %s.' % (ident)
        raise ResolverException(404, message)

    def cached_files_for_ident(self, ident):
        cache_dir = self.cache_dir_path(ident)
        if exists(cache_dir):
            return glob.glob(join(cache_dir, 'loris_cache.*'))
        return []

    def in_cache(self, ident):
        cache_dir = self.cache_dir_path(ident)
        if exists(cache_dir):
            cached_files = self.cached_files_for_ident(ident)
            if cached_files:
                return True
            else:
                log_message = 'Cached image not found for identifier: %s. Empty directory where image expected?' % (ident)
                logger.warn(log_message)
                self.raise_404_for_ident(ident)
        return False

    def cached_object(self, ident):
        cached_files = self.cached_files_for_ident(ident)
        if cached_files:
            cached_object = cached_files[0]
        else:
            self.raise_404_for_ident(ident)
        return cached_object

    def cache_file_extension(self, ident, response):
        if 'content-type' in response.headers:
            try:
                extension = self.format_from_ident(ident, constants.FORMATS_BY_MEDIA_TYPE[response.headers['content-type']])
            except KeyError:
                logger.warn('Your server may be responding with incorrect content-types. Reported %s for ident %s.'
                            % (response.headers['content-type'], ident))
                # Attempt without the content-type
                extension = self.format_from_ident(ident, None)
        else:
            extension = self.format_from_ident(ident, None)
        return extension

    def copy_to_cache(self, ident):
        ident = unquote(ident)
        source_url = self._web_request_url(ident)

        logger.debug('src image: %s' % (source_url,))

        try:
            response = requests.get(
                    source_url,
                    stream=False,
                    verify=self.ssl_check,
                    **self.request_options()
            )
        except requests.exceptions.MissingSchema:
            logger.warn(
                'Bad URL request at %s for identifier: %s.' % (source_url, ident)
            )
            public_message = 'Bad URL request made for identifier: %s.' % (ident,)
            raise ResolverException(404, public_message)

        if response.status_code != 200:
            public_message = 'Source image not found for identifier: %s. Status code returned: %s' % (ident,response.status_code)
            log_message = 'Source image not found at %s for identifier: %s. Status code returned: %s' % (source_url,ident,response.status_code)
            logger.warn(log_message)
            raise ResolverException(404, public_message)

        extension = self.cache_file_extension(ident, response)
        logger.debug('src extension %s' % (extension,))

        cache_dir = self.cache_dir_path(ident)
        local_fp = join(cache_dir, "loris_cache." + extension)

        try:
            makedirs(dirname(local_fp))
        except:
            logger.debug("Directory already existed... possible problem if not a different format")

        with open(local_fp, 'wb') as fd:
            for chunk in response.iter_content(2048):
                fd.write(chunk)

        logger.info("Copied %s to %s" % (source_url, local_fp))

    def resolve(self, ident):
        cache_dir = self.cache_dir_path(ident)
        if not exists(cache_dir):
            self.copy_to_cache(ident)
        cached_file_path = self.cached_object(ident)
        format = self.format_from_ident(cached_file_path, None)
        logger.debug('src image from local disk: %s' % (cached_file_path,))
        return (cached_file_path, format)


class TemplateHTTPResolver(SimpleHTTPResolver):
    '''HTTP resolver that suppors multiple configurable patterns for supported
    urls.  Based on SimpleHTTPResolver.  Identifiers in URLs should be
    specified as `template_name:id`.

    The configuration MUST contain
     * `cache_root`, which is the absolute path to the directory where source images
        should be cached.

    The configuration SHOULD contain
     * `templates`, a comma-separated list of template names e.g.
        templates=`site1,site2`
     * A url pattern for each specified template, e.g.
       site1='http://example.edu/images/%s' or site2='http://example.edu/images/%s/master'

    Note that if a template is listed but has no pattern configured, the
    resolver will warn but not fail.

    The configuration may also include the following settings, as used by
    SimpleHTTPResolver:
     * `default_format`, the format of images (will use content-type of
        response if not specified).
     * `head_resolvable` with value True, whether to make HEAD requests
        to verify object existence (don't set if using Fedora Commons
        prior to 3.8).  [Currently must be the same for all templates]
    '''
    def __init__(self, config):
        super(SimpleHTTPResolver, self).__init__(config)
        templates = self.config.get('templates', '')
        # technically it's not an error to have no templates configured,
        # but nothing will resolve; is that useful? or should this
        # cause an exception?
        if not templates:
            logger.warn('No templates specified in configuration')
        self.templates = {}
        for name in templates.split(','):
            name = name.strip()
            cfg = self.config.get(name, None)
            if cfg is None:
                logger.warn('No configuration specified for resolver template %s' % name)
            else:
                self.templates[name] = cfg

        # inherited/required configs from simple http resolver
        self.head_resolvable = self.config.get('head_resolvable', False)
        self.default_format = self.config.get('default_format', None)
        if 'cache_root' in self.config:
            self.cache_root = self.config['cache_root']
        else:
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Missing setting for cache_root.'
            logger.error(message)
            raise ResolverException(500, message)
        self.ident_regex = self.config.get('ident_regex', False)

        # required for simplehttpresolver
        # all templates are assumed to be uri resolvable
        self.uri_resolvable = True

        self.ssl_check = self.config.get('ssl_check', True)

    def _web_request_url(self, ident):
        # only split identifiers that look like template ids;
        # ignore other requests (e.g. favicon)
        if ':' not in ident:
            return
        prefix, ident = ident.split(':', 1)

        if 'delimiter' in self.config:
            # uses delimiter of choice from config file to split identifier
            # into tuple that will be fed to template
            ident_components = ident.split(self.config['delimiter'])
            if prefix in self.templates:
                return self.templates[prefix] % tuple(ident_components)
        else:
            if prefix in self.templates:
                return self.templates[prefix] % ident
        # if prefix is not recognized, no identifier is returned
        # and loris will return a 404

    def request_options(self):
        # currently no username/passsword supported
        return {}


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
        source_fp = self.source_file_path(ident)
        return exists(source_fp)

    def format_from_ident(self, ident):
        return ident.split('.')[-1]

    def source_file_path(self, ident):
        ident = unquote(ident)
        return join(self.source_root, ident)

    def cache_file_path(self, ident):
        ident = unquote(ident)
        return join(self.cache_root, ident)

    def in_cache(self, ident):
        return exists(self.cache_file_path(ident))

    def copy_to_cache(self, ident):
        source_fp = self.source_file_path(ident)
        cache_fp = self.cache_file_path(ident)

        makedirs(dirname(cache_fp))
        copy(source_fp, cache_fp)
        logger.info("Copied %s to %s" % (source_fp, cache_fp))

    def raise_404_for_ident(self, ident):
        source_fp = self.source_file_path(ident)
        public_message = 'Source image not found for identifier: %s.' % (ident,)
        log_message = 'Source image not found at %s for identifier: %s.' % (source_fp,ident)
        logger.warn(log_message)
        raise ResolverException(404, public_message)

    def resolve(self, ident):
        if not self.is_resolvable(ident):
            self.raise_404_for_ident(ident)
        if not self.in_cache(ident):
            self.copy_to_cache(ident)

        cache_fp = self.cache_file_path(ident)
        logger.debug('Image Served from local cache: %s' % (cache_fp,))

        format = self.format_from_ident(ident)
        logger.debug('Source format %s' % (format,))
        return (cache_fp, format)



