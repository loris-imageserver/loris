# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from constants import SRC_FORMATS_SUPPORTED
from log_config import get_logger
from os.path import join, exists, isfile
from urllib import unquote
import loris_exception

logger = get_logger(__name__)

# TODO: figure out an abstract class or interface

class Resolver(object):
	def __init__(self, config):
		self.cache_root = config['src_img_root']

	def is_resolvable(self, ident):
		"""
		Args:
			ident (str):
				The identifier for the image.
		Returns:
			bool
		"""
		ident = unquote(ident)
		fp = join(self.cache_root, ident)
		return exists(fp)

		# the idea here is that in some scenarios it may be cheaper to check 
		# that an id is resolvable than to actually resolve it and calculate the
		# fp.


	def resolve(self, ident):
		"""
		Given the identifier of an image, get the path (fp) and format. This 
		will likely	need to be reimplemented overridden to suit different 
		environments and can be as smart or dumb as you want.
		
		For this dumb version a constant path is prepended to the identfier 
		supplied to get the path It assumes this 'identifier' ends with a file 
		extension from which the format is then derived.

		For other formats you'll also need to implement a static constructor for
		ImgInfo to get what it needs from that format, i.e. ImgInfo.from_myformat().

		Args:
			ident (str):
				The identifier for the image.
		Returns:
			(str, str): (fp, format)
		Raises:
			ResolverException when something goes wrong...
		"""
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

		if format not in SRC_FORMATS_SUPPORTED:
 			public_message = 'Source image is not in a recognizable format %s' % (format,)
			log_message = 'Source image not found at %s' % (fp,)
 			logger.warn(log_message)
 			# todo: confirm status code. Maybe should be 500?
 			raise ResolverException(400, public_message)

		return (fp, format)

class ResolverException(loris_exception.LorisException): pass
