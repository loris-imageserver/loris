#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`resolver` -- Resolve Identifiers to Image Paths
==========================================================
.. module:: resolver
   :platform: Unix
   :synopsis: This module must include one function, `resolve` that takes one
   argument, an identifier, and returns a path to a JP2 on the file system.
.. moduleauthor:: Jon Stroop <jstroop@princeton.edu>

"""
from os.path import join
from werkzeug.routing import BaseConverter

SRC_IMG_ROOT='/home/jstroop/workspace/loris/test_img'

def resolve(ident):
	"""
	Given the identifier of an image, resolve it to an actual path. This
	would need to be overridden to suit different environments.
		
	This simple version just prepends a constant path to the identfier
	supplied, and appends a file extension, resulting in an absolute path 
	on the filesystem.
	"""
	return join(SRC_IMG_ROOT, ident.replace('%2F', '/') + '.jp2')

