"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from logging import getLogger
from os.path import join, exists, dirname, split
from os import remove
from shutil import copy
import tempfile
from contextlib import closing
import glob
import json
import os
from urllib.parse import unquote

import requests

from loris import constants
from loris.identifiers import CacheNamer, IdentRegexChecker
from loris.loris_exception import ResolverException
from loris.utils import mkdir_p, safe_rename
from loris.img_info import ImageInfo


logger = getLogger(__name__)


class _AbstractResolver(object):

    def __init__(self, config):
        self.config = config
        if config:
            self.auth_rules_ext = self.config.get('auth_rules_ext', 'rules.json')
            self.use_extra_info = self.config.get('use_extra_info', True)

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

    def resolve(self, app, ident, base_uri):
        """
        Given the identifier of an image, get the path (fp) and format (one of.
        'jpg', 'tif', or 'jp2'). This will likely need to be reimplemented for
        environments and can be as smart or dumb as you want.

        Args:
            ident (str):
                The identifier for the image.
        Returns:
            ImageInfo: Partially constructed ImageInfo object
        Raises:
            ResolverException when something goes wrong...
        """
        cn = self.__class__.__name__
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))

    def get_extra_info(self, ident, source_fp):
        """
        Given the identifier and any resolved source file, find the associated
        extra information to include in info.json, plus any additional authorizer
        specific information.  It might end up there after being copied by a
        caching implementation, or live there permanently.

        Args:
            ident (str):
                The identifier for the image
            source_fp (str):
                The source image filepath, if there is one
        Returns:
            dict: The dict of information to embed in info.json
        """
        xjsfp = source_fp.rsplit('.', 1)[0] + "." + self.auth_rules_ext
        if exists(xjsfp):
            fh = open(xjsfp)
            xjs = json.load(fh)
            fh.close()
            return xjs
        else:
            return {}

    def fix_base_uri(self, base_uri):
        return base_uri

    def format_from_ident(self, ident):
        if ident.rfind('.') != -1:
            extension = ident.split('.')[-1]
            if len(extension) < 5:
                extension = extension.lower()
                return constants.EXTENSION_MAP.get(extension, extension)
        raise ResolverException(
            "Format could not be determined for %r." % ident
        )


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
        raise ResolverException(message)

    def source_file_path(self, ident):
        ident = unquote(ident)
        for directory in self.source_roots:
            fp = join(directory, ident)
            if exists(fp):
                return fp

    def is_resolvable(self, ident):
        return not self.source_file_path(ident) is None

    def resolve(self, app, ident, base_uri):

        if not self.is_resolvable(ident):
            self.raise_404_for_ident(ident)

        source_fp = self.source_file_path(ident)
        format_ = self.format_from_ident(ident)
        uri = self.fix_base_uri(base_uri)
        extra = self.get_extra_info(ident, source_fp)
        return ImageInfo(app, uri, source_fp, format_, extra)


class ExtensionNormalizingFSResolver(SimpleFSResolver):
    '''This Resolver is deprecated - when resolving the identifier to an image
    format, all resolvers now automatically normalize (lower-case) file
    extensions and map 4-letter .tiff & .jpeg extensions to the 3-letter tif
    & jpg image formats Loris uses.
    '''
    pass


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
     * `ssl_check`, whether to check the validity of the origin server's HTTPS
     certificate. Set to False if you are using an origin server with a
     self-signed certificate.
     * `cert`, path to an SSL client certificate to use for authentication. If `cert` and `key` are both present, they take precedence over `user` and `pw` for authentication.
     * `key`, path to an SSL client key to use for authentication.
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

        self.cert = self.config.get('cert', None)

        self.key = self.config.get('key', None)

        self.ssl_check = self.config.get('ssl_check', True)

        self._ident_regex_checker = IdentRegexChecker(
            ident_regex=self.config.get('ident_regex')
        )
        self._cache_namer = CacheNamer()

        if 'cache_root' in self.config:
            self.cache_root = self.config['cache_root']
        else:
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Missing setting for cache_root.'
            logger.error(message)
            raise ResolverException(message)

        if not self.uri_resolvable and self.source_prefix == '':
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Must either set uri_resolvable' \
                      ' or source_prefix settings.'
            logger.error(message)
            raise ResolverException(message)

    def request_options(self):
        # parameters to pass to all head and get requests;
        options = {}
        if self.cert is not None and self.key is not None:
            options['cert'] = (self.cert, self.key)
        if self.user is not None and self.pw is not None:
            options['auth'] = (self.user, self.pw)
        options['verify'] = self.ssl_check
        return options

    def is_resolvable(self, ident):
        ident = unquote(ident)

        if not self._ident_regex_checker.is_allowed(ident):
            return False

        fp = self.cache_dir_path(ident=ident)
        if exists(fp):
            return True
        else:
            try:
                (url, options) = self._web_request_url(ident)
            except ResolverException:
                return False

            try:
                if self.head_resolvable:
                    response = requests.head(url, **options)
                    return response.ok
                else:
                    with closing(requests.get(url, stream=True, **options)) as response:
                        return response.ok
            except requests.ConnectionError:
                return False

    def get_format(self, ident, potential_format):
        if self.default_format is not None:
            return self.default_format
        elif potential_format is not None:
            return potential_format
        else:
            return self.format_from_ident(ident)

    def _web_request_url(self, ident):
        if ident.startswith(('http://', 'https://')) and self.uri_resolvable:
            url = ident
        else:
            url = self.source_prefix + ident + self.source_suffix
        if not url.startswith(('http://', 'https://')):
            logger.warn('Bad URL request at %s for identifier: %s.', url, ident)
            raise ResolverException(
                "Bad URL request made for identifier: %r." % ident
            )
        return (url, self.request_options())

    def cache_dir_path(self, ident):
        return os.path.join(
            self.cache_root,
            CacheNamer.cache_directory_name(ident=ident)
        )

    def raise_404_for_ident(self, ident):
        raise ResolverException("Image not found for identifier: %r." % ident)

    def cached_file_for_ident(self, ident):
        cache_dir = self.cache_dir_path(ident)
        if exists(cache_dir):
            files = glob.glob(join(cache_dir, 'loris_cache.*'))
            if files:
                return files[0]
        return None

    def cache_file_extension(self, ident, response):
        if 'content-type' in response.headers:
            try:
                extension = self.get_format(ident, constants.FORMATS_BY_MEDIA_TYPE[response.headers['content-type']])
            except KeyError:
                logger.warn('Your server may be responding with incorrect content-types. Reported %s for ident %s.',
                            response.headers['content-type'], ident)
                # Attempt without the content-type
                extension = self.get_format(ident, None)
        else:
            extension = self.get_format(ident, None)
        return extension

    def copy_to_cache(self, ident):
        ident = unquote(ident)

        #get source image and write to temporary file
        (source_url, options) = self._web_request_url(ident)
        assert source_url is not None

        cache_dir = self.cache_dir_path(ident)
        mkdir_p(cache_dir)

        with closing(requests.get(source_url, stream=True, **options)) as response:
            if not response.ok:
                logger.warn(
                    "Source image not found at %s for identifier: %s. "
                    "Status code returned: %s.",
                    source_url, ident, response.status_code
                )
                raise ResolverException(
                    "Source image not found for identifier: %s. "
                    "Status code returned: %s." % (ident, response.status_code)
                )

            extension = self.cache_file_extension(ident, response)
            local_fp = join(cache_dir, "loris_cache." + extension)

            with tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as tmp_file:
                for chunk in response.iter_content(2048):
                    tmp_file.write(chunk)

        # Now rename the temp file to the desired file name if it still
        # doesn't exist (another process could have created it).
        #
        # Note: This is purely an optimisation; if the file springs into
        # existence between the existence check and the copy, it will be
        # overridden.
        if exists(local_fp):
            logger.info('Another process downloaded src image %s', local_fp)
            remove(tmp_file.name)
        else:
            safe_rename(tmp_file.name, local_fp)
            logger.info("Copied %s to %s", source_url, local_fp)

        # Check for rules file associated with image file
        # These files are < 2k in size, so fetch in one go.
        # Assumes that the rules will be next to the image
        # cache_dir is image specific, so this is easy

        bits = split(source_url)
        fn = bits[1].rsplit('.', 1)[0] + "." + self.auth_rules_ext
        rules_url = bits[0] + '/' + fn
        try:
            resp = requests.get(rules_url)
            if resp.status_code == 200:
                local_rules_fp = join(cache_dir, "loris_cache." + self.auth_rules_ext)
                if not exists(local_rules_fp):
                    with open(local_rules_fp, 'w') as fh:
                        fh.write(resp.text)
        except:
            # No connection available
            pass

        return local_fp

    def resolve(self, app, ident, base_uri):
        cached_file_path = self.cached_file_for_ident(ident)
        if not cached_file_path:
            cached_file_path = self.copy_to_cache(ident)
        format_ = self.get_format(cached_file_path, None)
        uri = self.fix_base_uri(base_uri)
        if self.use_extra_info:
            extra = self.get_extra_info(ident, cached_file_path)
        else:
            extra = {}
        return ImageInfo(app, uri, cached_file_path, format_, extra)


class TemplateHTTPResolver(SimpleHTTPResolver):
    """
    An HTTP resolver that supports multiple configurable patterns for
    supported URLs.  It is based on SimpleHTTPResolver.  Identifiers in URLs
    should be specified as ``template_name:id``.

    It has the same mandatory config as SimpleHTTPResolver (must specify
    ``cache_root``, one of ``source_prefix`` or ``uri_resolvable=True``).

    The configuration should contain:

    *   ``templates``, a comma-separated list of template names.  For example:

            templates = 'site1,site2'

    *   A named subsection for each template.  This subsection MUST contain
        a ``url``, with a URL pattern for each template.  For example:

            [[site1]]
            url = 'http://example.edu/images/%'

            [[site2]]
            url = 'https://example.edu/images/%s/master'

        Each subsection MAY also contain other keys from the SimpleHTTPResolver
        configuration to provide a per-template override of each of these
        options -- ``user``, ``pw``, ``ssl_check``, ``cert`` and ``key``.

    If a template is listed but has no pattern configured, the resolver
    will warn but not error.

    If a template has multiple fill-in sections, you can pass a ``delimiter``
    option to the global config.  When an identifier is received, it will
    be split on this delimiter to get the different parts.  For example:

        templates = 'site'
        delimiter = '|'

        [[site]]
        url = 'http://example.edu/images/%/dir/%s'

    Making a request for identifier ``site:red|yellow`` would resolve to the
    URL ``http://example.edu/images/red/dir/yellow``.

    The configuration may also include the following settings, as used
    by SimpleHTTPResolver:

    *   ``default_format``, the format of images (will use the Content-Type
        of the response if unspecified)
    *   ``head_resolvable`` with value True, whether to make HEAD requests
        to validate object existence (don't set if using Fedora Commons
        prior to 3.8.)  [Currently must be the same for all templates.]

    """
    def __init__(self, config):
        # required for simplehttpresolver
        # all templates are assumed to be uri resolvable
        config['uri_resolvable'] = True
        super(TemplateHTTPResolver, self).__init__(config)
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
                logger.warn('No configuration specified for resolver template %s', name)
            else:
                self.templates[name] = cfg
        logger.debug('TemplateHTTPResolver templates: %s', self.templates)

    def _web_request_url(self, ident):
        # only split identifiers that look like template ids;
        # ignore other requests (e.g. favicon)
        if ':' not in ident:
            logger.warn('Bad URL request for identifier: %r.', ident)
            raise ResolverException(
                "Bad URL request made for identifier: %r." % ident
            )

        prefix, ident_parts = ident.split(':', 1)

        try:
            url_template = self.templates[prefix]['url']
        except KeyError:
            logger.warn('No template found for identifier: %r.', ident)
            raise ResolverException(
                "Bad URL request made for identifier: %r." % ident
            )

        try:
            url = url_template % tuple(ident_parts.split(self.config['delimiter']))
        except KeyError:
            url = url_template % ident_parts
        except TypeError as e:
            # Raised if there are more parts in the ident than spaces in
            # the template, e.g. '%s' % (1, 2).
            logger.warn('TypeError raised when processing identifier: %r (%r).', (ident, e))
            raise ResolverException(
                "Bad URL request made for identifier: %r." % ident
            )

        # Get the generic options
        options = self.request_options()
        # Then add any template-specific ones
        conf = self.templates[prefix]
        if 'cert' in conf and 'key' in conf:
            options['cert'] = (conf['cert'], conf['key'])
        if 'user' in conf and 'pw' in conf:
            options['auth'] = (conf['user'], conf['pw'])
        if 'ssl_check' in conf:
            options['verify'] = conf['ssl_check']
        return (url, options)


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

        mkdir_p(dirname(cache_fp))
        copy(source_fp, cache_fp)
        logger.info("Copied %s to %s", source_fp, cache_fp)

        # TODO: This should also check for and cache rules file

    def raise_404_for_ident(self, ident):
        source_fp = self.source_file_path(ident)
        logger.warn(
            "Source image not found at %s for identifier: %s.",
            source_fp, ident
        )
        raise ResolverException(
            "Source image not found for identifier: %s." % ident
        )

    def resolve(self, app, ident, base_uri):
        if not self.is_resolvable(ident):
            self.raise_404_for_ident(ident)
        if not self.in_cache(ident):
            self.copy_to_cache(ident)

        cache_fp = self.cache_file_path(ident)
        format_ = self.format_from_ident(ident)
        uri = self.fix_base_uri(base_uri)
        extra = self.get_extra_info(ident, cache_fp)
        return ImageInfo(app, uri, cache_fp, format_, extra)
