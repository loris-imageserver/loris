# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from os.path import join

SRC_IMG_ROOT='/usr/local/share/images'

def resolve(ident):
	"""
	Given the identifier of an image, resolve it to an actual path. This
	would need to be overridden to suit different environments.
		
	This simple version just prepends a constant path to the identfier
	supplied, and appends a file extension, resulting in an absolute path 
	on the filesystem.
	"""
	return join(SRC_IMG_ROOT, ident.replace('%2F', '/') + '.jp2')

