# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from log_config import get_logger
from os.path import join, exists, isfile
from urllib import unquote
import loris_exception

logger = get_logger(__name__)

class _AbstractResolver(object):
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
		self.cache_root = config['src_img_root']

	def is_resolvable(self, ident):
		ident = unquote(ident)
		fp = join(self.cache_root, ident)
		return exists(fp)

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
			raise ResolverException(400, public_message)

		format = ident.split('.')[-1]
		logger.debug('src format %s' % (format,))

		return (fp, format)

class ResolverException(loris_exception.LorisException): pass
