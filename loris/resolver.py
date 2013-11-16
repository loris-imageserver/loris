# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from log import get_logger
from os.path import join, exists, isfile
from urllib import unquote

import loris_exception

logger = get_logger(__name__)

class _AbstractResolver(object):
	def __init__(self, config):
		self.config = config

	def is_resolvable(self, ident):
		"""
		The idea here is that in some scenarios it may be cheaper to check 
		that an id is resolvable than to actually resolve it and retrieve or
		calculate the fp.

		Args:
			ident (str):
				The identifier for the image.
		Returns:
			bool
		"""
		e = self.__class__.__name__
		raise NotImplementedError('is_resolvable() not implemented for %s' % (cn,))

	def resolve(self, ident):
		"""
		Given the identifier of an image, get the path (fp) and format. This 
		will likely	need to be reimplemented overridden to suit different 
		environments and can be as smart or dumb as you want.
		
		Args:
			ident (str):
				The identifier for the image.
		Returns:
			(str, str): (fp, format)
		Raises:
			ResolverException when something goes wrong...
		"""
		e = self.__class__.__name__
		raise NotImplementedError('resolve() not implemented for %s' % (cn,))


class Resolver(_AbstractResolver):
	def __init__(self, config):
		super(Resolver, self).__init__(config)
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

		format = Resolver._format_from_ident(ident)
		logger.debug('src format %s' % (format,))

		return (fp, format)

class SourceImageCachingResolver(Resolver):
	from shutil import copy
	from os import makedirs
	from os.path import dirname


	def __init__(self, config, disk_cache_root):
		super(Resolver, self).__init__(config)
		self.disk_cache_root = disk_cache_root

	def resolve(self, ident):
		ident = unquote(ident)
		local_fp = join(self.disk_cache_root, ident)

		if exists(local_fp):
			format = SourceImageCachingResolver._format_from_ident(ident)
			logger.debug('src image from local disk: %s' % (local_fp,))
			return (local_fp, format)
		else:
			fp = join(self.cache_root, ident)
			logger.debug('src image: %s' % (fp,))
			if not exists(fp):
				public_message = 'Source image not found for identifier: %s.' % (ident,)
				log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
				logger.warn(log_message)
				raise ResolverException(400, public_message)

			makedirs(dirname(local_fp))
			copy(fp, local_fp)
			logger.info("Copied %s to %s" % (fp, local_fp))

			format = SourceImageCachingResolver._format_from_ident(ident)
			logger.debug('src format %s' % (format,))

			return (local_fp, format)



class ResolverException(loris_exception.LorisException): pass
