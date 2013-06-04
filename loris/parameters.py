# parameters.py
# -*- coding: utf-8 -*-

'''
IIIF Image API parameters as objects. 

The attributes of this class should make it possible to work with most imaging
libraries without any further need to process the IIIF syntax. 
'''

from decimal import Decimal
from log_config import get_logger
from loris_exception import LorisException
import abc

logger = get_logger(__name__)

class RegionParameter(object):
	'''Internal representation of the region slice of an IIIF image URI.

	Slots:
		uri_value (str): 
			The region slice of the URI.
		cannonical_uri_value (str): 
			The normalized (pixel-based, in-bounds) region slice of the URI.
		mode (str): 
			One of 'full', 'pct', or 'pixel'
		img_info (ImageInfo)
		pixel_x (int)
		decimal_x (Decimal)
		pixel_y (int)
		decimal_y (Decimal)
		pixel_w (int)
		decimal_w (Decimal)
		pixel_h (int)
		decimal_h (Decimal)
	'''
	__slots__ = (
		'uri_value',
		'cannonical_uri_value',
		'pixel_x', 
		'decimal_x', 
		'pixel_y', 
		'decimal_y', 
		'pixel_w', 
		'decimal_w', 
		'pixel_h', 
		'decimal_h', 
		'mode', 
		'img_info'
	)

	FULL_MODE = 'full'
	PCT_MODE = 'pct'
	PIXEL_MODE = 'pixel'
	DECIMAL_ONE = Decimal(1.0)

	def __str__(self):
		return self.uri_value

	def __init__(self, uri_value, img_info):
		'''Parse the uri_value into the object.

		Args:
			uri_value (str): The region slice of an IIIF image request URI.
			img_info (ImgInfo)

		Raises:
			BadRegionSyntaxException
			BadRegionRequestException
		'''
		self.uri_value = uri_value
		self.img_info = img_info
		try:
			self.mode = RegionParameter.__mode_from_region_segment(self.uri_value)
			logger.debug('Region mode is "%s" (from "%s")' % (self.mode,uri_value))
		except BadRegionSyntaxException:
			raise

		if self.mode != RegionParameter.FULL_MODE:
			try:
				if self.mode == RegionParameter.PCT_MODE:
					self.__populate_slots_from_pct()
				else: # self.mode == RegionParameter.PIXEL_MODE: 
					self.__populate_slots_from_pixels()
			except (BadRegionSyntaxException, BadRegionRequestException):
				raise

			logger.debug('decimal_x: %s' % (str(self.decimal_x),))
			logger.debug('pixel_x: %d' % (self.pixel_x,))
			logger.debug('decimal_y: %s' % (str(self.decimal_y),))
			logger.debug('pixel_y: %d' % (self.pixel_y,))
			logger.debug('decimal_w: %s' % (str(self.decimal_w),))
			logger.debug('pixel_w: %d' % (self.pixel_w,))
			logger.debug('decimal_h: %s' % (str(self.decimal_h),))
			logger.debug('pixel_h: %d' % (self.pixel_h,))

			# Adjust OOB requests that are allowed
			# TODO: consider raising an exception that we can use to redirect
			if (self.decimal_x + self.decimal_w) > RegionParameter.DECIMAL_ONE:
				self.decimal_w = RegionParameter.DECIMAL_ONE - self.decimal_x
				self.pixel_w = img_info.width - self.pixel_x
				logger.info('decimal_w adjusted to: %s' % (str(self.decimal_w)),)
				logger.info('pixel_w adjusted to: %d' % (self.pixel_w,))
			if (self.decimal_y + self.decimal_h) > RegionParameter.DECIMAL_ONE: 
				self.decimal_h = RegionParameter.DECIMAL_ONE - self.decimal_y
				self.pixel_h = img_info.height - self.pixel_y
				logger.info('decimal_h adjusted to: %s' % (str(self.decimal_h)),)
				logger.debug('pixel_h adjusted to: %s' % (str(self.pixel_h)),)

			# Catch OOB errors:
			if any(axis < 0 for axis in (self.pixel_x, self.pixel_y)):
				msg = 'x and y region parameters must be 0 or greater (%s)' % (self.uri_value,)
				raise BadRegionRequestException(http_status=400, message=msg)
			if self.decimal_x >= RegionParameter.DECIMAL_ONE:
				msg = 'Region x parameter is greater than the width of the image.\n'
				msg +='Image width is %d' % (img_info.width,)
				raise BadRegionRequestException(http_status=400, message=msg)
			if self.decimal_x >= RegionParameter.DECIMAL_ONE:
				msg = 'Region y parameter is greater than the height of the image.\n'
				msg +='Image height is %d' % (img_info.height,)
				raise BadRegionRequestException(http_status=400, message=msg)

			# set cannonical_uri_value to the equivalent pixel-based syntax after
			# all adjustments have been made.
			px = (self.pixel_x, self.pixel_y, self.pixel_w, self.pixel_h)
			self.cannonical_uri_value = ','.join(map(str, px))
			logger.debug('Cannonical uri_value %s' % (self.cannonical_uri_value,))

	def __populate_slots_from_pct(self):
		'''
		Raises:
			BadRegionSyntaxException
			BadRegionRequestException
		'''
		# we convert these to pixels and update uri_value
		dimensions = map(float, self.uri_value.split(':')[1].split(',')) 

		if len(dimensions) != 4:
			msg = 'Exactly (4) coordinates must be supplied'
			raise BadRegionSyntaxException(http_status=400, message=msg)
		if any(n > 100.0 for n in dimensions):
			msg = 'Region percentages must be less than or equal to 100.'
			raise BadRegionRequestException(http_status=400, message=msg)
		if any((n <= 0) for n in dimensions[2:]):
			msg = 'Width and Height Percentages must be greater than 0.'
			raise BadRegionRequestException(http_status=400, message=msg)

		# decimals
		self.decimal_x, self.decimal_y,	self.decimal_w,	\
			self.decimal_h = map(RegionParameter.__pct_to_decimal, dimensions)

		# pixels
		self.pixel_x = int(round(self.decimal_x * self.img_info.width))
		self.pixel_y = int(round(self.decimal_y * self.img_info.height))
		self.pixel_w = int(round(self.decimal_w * self.img_info.width))
		self.pixel_h = int(round(self.decimal_h * self.img_info.height))

	def __populate_slots_from_pixels(self):
		'''
		Raises:
			BadRegionRequestException
			BadRegionSyntaxException
		'''
		dimensions = map(int, self.uri_value.split(','))

		if any(n <= 0 for n in dimensions[2:]):
			msg = 'Width and height must be greater than 0'
			raise BadRegionRequestException(http_status=400, message=msg)
		if len(dimensions) != 4:
			msg = 'Exactly (4) coordinates must be supplied'
			raise BadRegionSyntaxException(http_status=400, message=msg)
		
		# pixels
		self.pixel_x, self.pixel_y, self.pixel_w, self.pixel_h = dimensions

		# decimals
		self.decimal_x = self.pixel_x / Decimal(self.img_info.width)
		self.decimal_y = self.pixel_y / Decimal(self.img_info.height)
		self.decimal_w = self.pixel_w / Decimal(self.img_info.width)
		self.decimal_h = self.pixel_h / Decimal(self.img_info.height)

	@staticmethod
	def __mode_from_region_segment(region_segment):
		'''
		Get the mode of the request from the region segment.

		Args:
			region_segment (str)
		Returns:
			RegionParameter.PCT_MODE, RegionParameter.FULL_MODE, or
			RegionParameter.PIXEL_MODE
		Raises:
			BadRegionSyntaxException if this can't be determined.
		'''
		if region_segment.split(':')[0] == 'pct':
			return RegionParameter.PCT_MODE
		elif region_segment == 'full':
			return RegionParameter.FULL_MODE
		elif all([n.isdigit() for n in region_segment.split(',')]):
			return RegionParameter.PIXEL_MODE
		else:
			msg = 'Region syntax "%s" is not valid' % (region_segment,)
			raise BadRegionSyntaxException(http_status=400, message=msg)

	@staticmethod
	def __pct_to_decimal(n):
		return Decimal(n) / Decimal(100.0)

class BadRegionSyntaxException(LorisException): pass
class BadRegionRequestException(LorisException): pass
	# # TODO: move
	# def to_kdu_arg(self, img_info):
	# 	cmd = ''
	# 	if self.mode != 'full':
	# 		cmd = '-region '
	# 		# The precision of regular floats is frequently not enough, hence 
	# 		# the use of Decimal.
	# 		top,left,height,width = self.as_decimals(img_info)

	# 		# "If the request specifies a region which extends beyond the 
	# 		# dimensions of the source image, then the service should return an 
	# 		# image cropped at the boundary of the source image."
	# 		cmd += '\{%s,%s\},\{%s,%s\}' % (top, left, height, width)
	# 		#logr.debug('kdu region parameter: ' + cmd)
	# 	return cmd


# class SizeParameter(object):
# 	'''Internal representation of the size slice of an IIIF image URI.

# 	Slots:
# 		uri_value (str): The region slice of the URI.
# 		mode (str): One of 'full', 'pct', or 'pixel'
#		cannonical_uri_value (str)
# 		force_aspect (bool): True if the aspect ratio of the image should not
# 			be preserved.
# 		w (int): The width.
# 		h (int): The height.
# 	'''
# 	__slots__ = ('uri_value', 'cannonical_uri_value', 'mode', 'force_aspect', 'pct', 'w', 'h')

# 	def __init__(self, uri_value, img_info):
# 		'''Parse the URI slice into an object.
# 		Args:
# 			uri_value: The size slice of an IIIF image URI.

# 		Raises:
# 			BadSizeSyntaxException if we have trouble parsing the request.
# 		'''
# 		self.uri_value = uri_value

# 		pct_or_full = uri_value.split(':')[0]
# 		self.mode = pct_or_full if pct_or_full in ('pct', 'full') else 'pixel'
# 		self.force_aspect = None
#		self.cannonical_uri_value = None
# 		self.pct = None
# 		self.w, self.h = [None, None]
# 		try:
# 			if self.mode == 'pct':
# 				self.pct = float(self.uri_value.split(':')[1])
# 				if self.pct <= 0:
# 					msg = 'Percentage supplied is less than 0. '
# 					raise BadSizeSyntaxException(400, self.uri_value, msg)

# 			elif self.mode == 'pixel':
# 				if self.uri_value.endswith(','):
# 					self.w = int(self.uri_value[:-1])
# 				elif self.uri_value.startswith(','):
# 					self.h = int(self.uri_value[1:])
# 				elif self.uri_value.startswith('!'):
# 					self.force_aspect = False
# 					self.w, self.h = map(int, self.uri_value[1:].split(','))
# 				else:
# 					self.force_aspect = True
# 					self.w, self.h = map(int, self.uri_value.split(','))
# 			else:
# 				if self.mode != 'full':
# 					msg = 'Could not parse Size parameter.'
# 					raise BadSizeSyntaxException(400, self.uri_value, msg)

# 		except Exception, e:
# 			msg = 'Bad size syntax. ' + e.message
# 			raise BadSizeSyntaxException(400, self.uri_value, msg)
		
# 		if any((dim < 1 and dim != None) for dim in (self.w, self.h)):
# 			msg = 'Width and height must both be positive numbers'
# 			raise BadSizeSyntaxException(400, self.uri_value, msg)

# 	def __str__(self):
# 		return self.uri_value
		
# 	def __repr__(self):
# 		return self.uri_value

# 	# TODO: MOVE. 
# 	# TODO A method that turns pct size requests into pixel dims for the cache
# 	def to_convert_arg(self):
# 		'''Construct a `-resize <geometry>` argument for the convert utility.

# 		Returns:
# 			str.

# 		Raises:
# 			BadSizeSyntaxException.
# 		'''
# 		cmd = ''
# 		if self.uri_value != 'full':
# 			cmd = '-resize '
# 			if self.mode == 'pct':
# 				cmd += str(self.pct) + '%'
# 			elif self.w and not self.h:
# 				cmd += str(self.w)
# 			elif self.h and not self.w:
# 				cmd += 'x' + str(self.h)
# 			# IIIF and Imagmagick use '!' in opposite ways: to IIIF, the 
# 			# presense of ! means that the aspect ratio should be preserved, to
# 			# `convert` it means that it should be ignored.
# 			elif self.w and self.h and not self.force_aspect:
# 				cmd +=  str(self.w) + 'x' + str(self.h) #+ '\>'
# 			elif self.w and self.h and self.force_aspect:
# 				cmd += str(self.w) + 'x' + str(self.h) + '!'
# 			else:
# 				msg = 'Could not construct a convert argument from ' + self.uri_value
# 				raise BadSizeRequestException(500, msg)
# 		return cmd

# class RotationParameter(object):
# 	'''Internal representation of the rotation slice of an IIIF image URI.

# 	Slots:
# 		nearest_90 (int). Any value passed is rounded to the nearest multiple
# 			of 90.
# 	'''
# 	__slots__ = ('uri_value', 'nearest_90')
# 	def __init__(self, uri_value):
# 		'''Take the uri value and round it to the nearest 90.
# 		Args:
# 			uri_value (str): the rotation slice of the request URI.
# 		Raises:
# 			BadRotationSyntaxException if we can't handle the value for some
# 				reason.
# 		'''
# 		self.uri_value = uri_value
# 		try:
# 			self.nearest_90 = int(90 * round(float(self.uri_value) / 90))
# 		except Exception, e:
# 			raise BadRotationSyntaxException(400, self.uri_value, e.message)

# 	def __str__(self):
# 		return self.uri_value

# 	def __repr__(self):
# 		return self.uri_value

# 	def to_convert_arg(self):
# 		'''Get a `-rotate` argument for the `convert` utility.

# 		Returns:
# 			str. E.g. `-rotate 180`.
# 		'''
# 		arg = ''
# 		if self.nearest_90 % 360 != 0: 
# 			arg = '-rotate ' + str(self.nearest_90)
# 		return arg


class BadSizeSyntaxException(LorisException): pass
class BadSizeRequestException(LorisException): pass
class BadRotationSyntaxException(LorisException): pass