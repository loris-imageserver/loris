# -*- coding: utf-8 -*-
'''
s3resolver.py
=========
Resolves source images stored in an Amazon S3 bucket.

AWS S3 credentials may be supplied to Boto in various ways
on the host system.  They are not referenced explicitly in
this code.

Configuration file should set source_root to S3 bucket URL
e.g.
   impl = 'loris.s3resolver.S3Resolver'
   source_root='s3://<bucket name>/'
'''
from loris_exception import ResolverException
from loris.resolver import _AbstractResolver
from loris.resolver import SimpleHTTPResolver
from urllib import unquote
import urlparse
from os import makedirs
from os.path import join, exists, dirname
import boto3
import botocore
import logging

import glob

logger = logging.getLogger(__name__)


class S3Resolver(_AbstractResolver):
    '''
    Resolver for images coming from AWS S3 bucket.
    The config dictionary MUST contain
     * `cache_root`, which is the absolute path to the directory where source images
        should be cached.
     * `source_root`, the s3 root for source images.
    '''
    def __init__(self, config):
        ''' setup object and validate '''
        super(S3Resolver, self).__init__(config)
        self.cache_root = self.config.get('cache_root')
        self.default_format = self.config.get('default_format', None)
        source_root = self.config.get('source_root')
        assert source_root, 'please set SOURCE_ROOT in environment'
        scheme, self.s3bucket, self.prefix, ___, ___ = urlparse.urlsplit(
            source_root
        )
        assert scheme == 's3', '{0} not an s3 url'.format(source_root)



    def is_resolvable(self, ident):
        '''does this file even exist?'''
        ident = unquote(ident)
        logger.debug('is_resolvable called with ident = %s', ident)
        local_fp = join(self.cache_root, ident)
        if exists(local_fp):
            return True
        else:
            # check that we can get to this object on S3
            s3 = boto3.resource('s3')

            try:
                # Strip off everything in the URL after the filename
                #key = ident.split('/')[0]
                key = ident
                logger.debug('Checking existence of Bucket = %s   Filename = %s', self.s3bucket, key)
                s3.Object(self.s3bucket, key).load()
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    logger.debug('Check for file returned HTTP CODE = 404')
                    return False

            logger.debug('is_resolvable = True')
            return True

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


    def copy_to_cache(self, ident):
        ident = unquote(ident)
        source_url = self._web_request_url(ident)

        logger.debug('src image: %s' % (source_url,))

        extension = self.format_from_ident(ident, None)
        logger.debug('src extension %s' % (extension,))

        cache_dir = self.cache_dir_path(ident)
        local_fp = join(cache_dir, "loris_cache." + extension)

        try:
            logger.debug('Trying to make directory |%s|' % local_fp)
            makedirs(dirname(local_fp))
        except:
            logger.debug("Directory already existed... possible problem if not a different format")


        # Download the image from S3
        bucketname = self.s3bucket
        logger.debug('Getting img from AWS S3. bucketname, key: %s, %s' % (bucketname, ident))
        s3_client = boto3.client('s3')
        s3_client.download_file(bucketname, ident, local_fp)

        logger.info("Copied %s to %s" % (source_url, local_fp))

    def cache_dir_path(self, ident):
        ident = unquote(ident)
        return join(
                self.cache_root,
                SimpleHTTPResolver._cache_subroot(ident)
        )

    def _web_request_url(self, ident):
        return ident


    def resolve(self, ident):
        cache_dir = self.cache_dir_path(ident)
        logger.debug('Checking for existence of cache_dir =  %s' % (cache_dir,))
        if not exists(cache_dir):
            logger.debug('copying source file to %s' % (cache_dir,))
            self.copy_to_cache(ident)
        cached_file_path = self.cached_object(ident)
        format = self.format_from_ident(cached_file_path, None)
        logger.debug('returning src image from local disk: %s' % (cached_file_path,))
        return (cached_file_path, format)
