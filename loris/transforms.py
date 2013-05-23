# transformation.py
# -*- coding: utf-8 -*-
'''
Image Transformtion Methods
===========================
Methods and configuration for transforming images between formats.
Author: Jon Stroop <jstroop@princeton.edu>
Since: 2013-05-17

All public methods in this module must follow this signature:

{src}_to_{deriv}(src_fp, src_fmt, region, size, rotation, 
	quality, deriv_fmt) -> file

Where:
	src_fp (str): 
		is the _absolute_ path to a the source image file.
	src_fmt (str from constants.FORMATS_BY_MEDIA_TYPE): 
		is the media type of the source image.
	region (parameters.RegionParameter): 
		is the region of the request.
	size (parameters.SizeParameter): 
		is size of the request.
	rotation (parameters.RotationParameter): 
		is the rotation of the request.
	quality (str from parameters.QUALITIES): 
		is the quality portion of the request.
	deriv_fmt (str from constants.FORMATS_BY_MEDIA_TYPE):
		is the media type of the source image.

All MUST return a file or file-like object
# TODO (I think...maybe just a str that points to the file would be OK. TBD)

Note that the parameter classes passed in (RegionParameter, SizeParameter, 
RotationParameter) should encapsulate most of the normalization of the incoming
request that the functions in this module need to do their work, e.g. in the 
case of size, the SizeParameter class will handle turning the IIIF API pct or 
w,h (etc.) syntax into the Decimal arguments that most imaging libraries want. 
See the properties and methods of those classes for details.
'''

# the name of this is a little misleading
CACHE_ROOT = None 
TMP_ROOT = None






def jp2_to_jpg(src_fp, src_fmt, region, size, rotation, quality, deriv_fmt):
	pass

def jp2_to_png(src_fp, src_fmt, region, size, rotation, quality, deriv_fmt):
	pass

def jpg_to_jpg(src_fp, src_fmt, region, size, rotation, quality, deriv_fmt):
	pass

def jpg_to_png(src_fp, src_fmt, region, size, rotation, quality, deriv_fmt):
	pass