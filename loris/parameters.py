#parameters.py
from decimal import Decimal
from loris.exceptions import BadRegionRequestException
from loris.exceptions import BadRegionSyntaxException
from loris.exceptions import BadSizeSyntaxException
from loris.exceptions import BadRotationSyntaxException

class RegionParameter(object):
	"""Internal representation of the region slice of an IIIF image URI.

	Slots:
		uri_value (str): The region slice of the URI.
		mode (str): One of 'full', 'pct', or 'pixel'
		x (float)
		y (float)
		w (float)
		h (float)
	"""
	__slots__ = ('uri_value', 'x', 'y', 'w', 'h', 'mode')
	def __init__(self, uri_value):
		"""Parse the uri_value into the object.

		Args:
			uri_value: The region slice of an IIIF image request URI.

		Raises:
			BadRegionSyntaxException
		"""
		self.uri_value = uri_value
		# self.x, self.y, self.w, self.h = [None, None, None, None]
		self.mode = uri_value.split(':')[0]
		if self.mode != 'full':
			try:
				v = uri_value.split(':')[1] if self.mode == 'pct' else uri_value
				dimensions = map(float, v.split(','))
				if self.mode == 'pct':
					if any(n > 100.0 for n in dimensions):
						msg = 'Percentages must be less than or equal to 100.'
						raise BadRegionSyntaxException(400, uri_value, msg)
					if any((n <= 0) for n in dimensions[2:]):
						msg = 'Width and Height Percentages must be greater than 0.'
						raise BadRegionSyntaxException(400, uri_value, msg)
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, uri_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
				else:
					self.mode = 'pixel'
					#logr.debug('Pixel dimensions request: ' + uri_value)
					if any(n <= 0 for n in dimensions[2:]):
						msg = 'Width and height must be greater than 0'
						raise BadRegionSyntaxException(400, uri_value, msg)
					if len(dimensions) != 4:
						msg = 'Exactly (4) coordinates must be supplied'
						raise BadRegionSyntaxException(400, uri_value, msg)
					self.x,	self.y, self.w,	self.h = dimensions
			except Exception, e :
				msg = 'Region syntax not valid. ' + e.message
				raise BadRegionSyntaxException(400, uri_value, msg)

	def __str__(self):
		return self.uri_value

	def to_kdu_arg(self, img_info):
		"""Turn the URI parameter into a `-region` argument for kdu_expand.

		For regions kdu wants \{<top>,<left>\},\{<height>,<width>\} (shell 
		syntax), as decimals between 0 and 1.

		IIIF supplies left[x], top[y], witdth[w], height[h] as percentages or
		pixel coordinates.

		Args:
			img_info (ImgInfo).

		Returns:
			str. The region argument to be passsed to kdu_expand.

		Raises:
			BadRegionRequestException when the region request includes a 
			number or the entire region would be out of bounds.
		"""
		cmd = ''
		if self.mode != 'full':
			cmd = '-region '
			# The precision of regular floats is frequently not enough, hence 
			# the use of Decimal.
			top,left,height,width = (None,None,None,None)
			if self.mode == 'pct':
				## TODO: PCT MODE IS BROKEN
				top = Decimal(self.y) / Decimal(100.0)
				left = Decimal(self.x) / Decimal(100.0)
				height = Decimal(self.h) / Decimal(100.0)
				width = Decimal(self.w) / Decimal(100.0)
			else:
				top = Decimal(self.y) / img_info.height
				left = Decimal(self.x) / img_info.width
				height = Decimal(self.h) / img_info.height
				width = Decimal(self.w) / img_info.width

			# "If the request specifies a region which extends beyond the 
			# dimensions of the source image, then the service should return an 
			# image cropped at the boundary of the source image."
			if (width + left) > Decimal(1.0):
				width = Decimal(1.0) - Decimal(left)
				#logr.debug('Width adjusted to: ' + str(width))
			if (top + height) > Decimal(1.0): 
				height = Decimal(1.0) - Decimal(top)
				#logr.debug('Height adjusted to: ' + str(height))
			# Catch OOB errors:
			# top and left
			if any(axis < 0 for axis in (top, left)):
				msg = 'x and y region paramaters must be 0 or greater'
				raise BadRegionRequestException(400, self.uri_value, msg)
			if left >= Decimal(1.0):
				msg = 'Region x parameter is out of bounds.\n'
				msg += str(self.x) + ' was supplied and image width is ' 
				msg += str(img_info.width)
				raise BadRegionRequestException(400, self.uri_value, msg)
			if top >= Decimal(1.0):
				msg = 'Region y parameter is out of bounds.\n'
				msg += str(self.y) + ' was supplied and image height is ' 
				msg += str(img_info.height) 
				raise BadRegionRequestException(400, self.uri_value, msg)
			cmd += '\{%s,%s\},\{%s,%s\}' % (top, left, height, width)
			#logr.debug('kdu region parameter: ' + cmd)
		return cmd


class SizeParameter(object):
	"""
	Internal representation of the size slice of an IIIF image URI.

	Slots:
		uri_value (str): The region slice of the URI.
		mode (str): One of 'full', 'pct', or 'pixel'
		force_aspect (bool): True if the aspect ration of the image should not
			be preserved.
		w (int): The width.
		h (int): The height.
	"""
	__slots__ = ('uri_value', 'mode', 'force_aspect', 'pct', 'w', 'h')
	def __init__(self, uri_value):
		"""Parse the URI slice into an the object.
		Args:
			uri_value: The size slice of an IIIF image URI.

		Raises:
			BadSizeSyntaxException if we have trouble parsing the request.
		"""
		self.uri_value = uri_value
		_token = uri_value.split(':')[0]
		self.mode = _token if _token in ('pct', 'full') else 'pixel'
		self.force_aspect = None
		self.pct = None
		self.w, self.h = [None, None]
		try:
			if self.mode == 'pct':
				try:
					self.pct = float(self.uri_value.split(':')[1])
					if self.pct <= 0:
						msg = 'Percentage supplied is less than 0. '
						raise BadSizeSyntaxException(400, self.uri_value, msg)
				except:
					raise

			elif self.mode == 'pixel':
				try:
					if self.uri_value.endswith(','):
						self.w = int(self.uri_value[:-1])
					elif self.uri_value.startswith(','):
						self.h = int(self.uri_value[1:])
					elif self.uri_value.startswith('!'):
						self.force_aspect = False
						self.w, self.h = map(int, self.uri_value[1:].split(','))
					else:
						self.force_aspect = True
						self.w, self.h = map(int, self.uri_value.split(','))
				except:
					raise
			else:
				if self.mode != 'full':
					msg = 'Could not parse Size parameter.'
					raise BadSizeSyntaxException(400, self.uri_value, msg)
		except Exception, e:
			msg = 'Bad size syntax. ' + e.message
			raise BadSizeSyntaxException(400, self.uri_value, msg)
		
		if any((dim < 1 and dim != None) for dim in (self.w, self.h)):
			msg = 'Width and height must both be positive numbers'
			raise BadSizeSyntaxException(400, self.uri_value, msg)

	def __str__(self):
		return self.uri_value
		
	def to_convert_arg(self):
		"""Construct a `-resize <geometry>` argument for the convert utility.

		Returns:
			str.

		Raises:
			BadSizeSyntaxException.
		"""
		cmd = ''
		if self.uri_value != 'full':
			cmd = '-resize '
			if self.mode == 'pct':
				cmd += str(self.pct) + '%'
			elif self.w and not self.h:
				cmd += str(self.w)
			elif self.h and not self.w:
				cmd += 'x' + str(self.h)
			# IIIF and Imagmagick use '!' in opposite ways: to IIIF, the 
			# presense of ! means that the aspect ratio should be preserved, to
			# `convert` it means that it should be ignored.
			elif self.w and self.h and not self.force_aspect:
				cmd +=  str(self.w) + 'x' + str(self.h) #+ '\>'
			elif self.w and self.h and self.force_aspect:
				cmd += str(self.w) + 'x' + str(self.h) + '!'
			else:
				msg = 'Could not construct a convert argument from ' + self.uri_value
				raise BadSizeRequestException(500, msg)
		return cmd

class RotationParameter(object):
	"""Internal representation of the rotation slice of an IIIF image URI.

	Slots:
		nearest_90 (int). Any value passed is rounded to the nearest multiple
			of 90.
	"""
	__slots__ = ('uri_value', 'nearest_90')
	def __init__(self, uri_value):
		"""Take the uri value and round it to the nearest 90.
		Args:
			uri_value (str): the rotation slice of the request URI.
		Raises:
			BadRotationSyntaxException if we can't handle the value for some
				reason.
		"""
		self.uri_value = uri_value
		try:
			self.nearest_90 = int(90 * round(float(self.uri_value) / 90))
		except Exception, e:
			raise BadRotationSyntaxException(400, self.uri_value, e.message)

	def __str__(self):
		return self.uri_value

	def to_convert_arg(self):
		"""Get a `-rotate` argument for the `convert` utility.

		Returns:
			str. E.g. `-rotate 180`.
		"""
		arg = ''
		if self.nearest_90 % 360 != 0: 
			arg = '-rotate ' + str(self.nearest_90)
		return arg
from loris.exceptions import BadSizeRequestException