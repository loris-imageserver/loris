# parameters.py
# -*- coding: utf-8 -*-

'''
IIIF Image API parameters as objects.

The attributes of this class should make it possible to work with most imaging
libraries without any further need to process the IIIF syntax.
'''

from __future__ import absolute_import

import re
from decimal import Decimal
from math import floor
from logging import getLogger

from loris.loris_exception import RequestException, SyntaxException

logger = getLogger(__name__)

FULL_MODE = 'full'
SQUARE_MODE = 'square'
PCT_MODE = 'pct'
PIXEL_MODE = 'pixel'
DECIMAL_ONE = Decimal('1.0')

class RegionParameter(object):
    '''Internal representation of the region slice of an IIIF image URI.

    Slots:
        uri_value (str):
            The region slice of the URI.
        canonical_uri_value (str):
            The normalized (pixel-based, in-bounds) region slice of the URI.
        mode (str):
            One of 'full', 'square', 'pct', or 'pixel'
        image_info (ImageInfo)
        pixel_x (int)
        decimal_x (Decimal)
        pixel_y (int)
        decimal_y (Decimal)
        pixel_w (int)
        decimal_w (Decimal)
        pixel_h (int)
        decimal_h (Decimal)
    '''
    __slots__ = ('uri_value','canonical_uri_value','pixel_x','decimal_x',
        'pixel_y','decimal_y','pixel_w','decimal_w','pixel_h','decimal_h',
        'mode','image_info')

    def __str__(self):
        return self.uri_value

    def __init__(self, uri_value, image_info):
        '''Parse the uri_value into the object.

        Args:
            uri_value (str): The region slice of an IIIF image request URI.
            image_info (ImgInfo)

        Raises:
            SyntaxException
            RequestException
        '''
        self.uri_value = uri_value
        self.image_info = image_info

        self.mode = RegionParameter._mode_from_region_segment(self.uri_value, self.image_info)

        logger.debug('Region mode is "%s" (from "%s")', self.mode, uri_value)

        if self.mode == FULL_MODE:
            self._populate_slots_for_full()
        elif self.mode == PIXEL_MODE:
            dimensions = self._pixel_dims_to_ints()
            self._populate_slots_from_pixels(dimensions)
        elif self.mode == SQUARE_MODE:
            self._populate_slots_for_square()
        else: # self.mode == PCT_MODE:
            self._populate_slots_from_pct()

        logger.debug('decimal_x: %s', self.decimal_x)
        logger.debug('pixel_x: %d', self.pixel_x)
        logger.debug('decimal_y: %s', self.decimal_y)
        logger.debug('pixel_y: %d', self.pixel_y)
        logger.debug('decimal_w: %s', self.decimal_w)
        logger.debug('pixel_w: %d', self.pixel_w)
        logger.debug('decimal_h: %s', self.decimal_h)
        logger.debug('pixel_h: %d', self.pixel_h)

        self._canonicalize()

    def _canonicalize(self):
        self._check_for_oob_errors()
        self._adjust_to_in_bounds()
        # set canonical_uri_value to the equivalent pixel-based syntax after
        # all adjustments have been made.
        if self.mode != FULL_MODE:
            px = (self.pixel_x, self.pixel_y, self.pixel_w, self.pixel_h)
            self.canonical_uri_value = ','.join([str(p) for p in px])
        else:
            self.canonical_uri_value = FULL_MODE
        logger.debug('canonical uri_value for region %s', self.canonical_uri_value)

    def _adjust_to_in_bounds(self):
        if (self.decimal_x + self.decimal_w) > DECIMAL_ONE:
            self.decimal_w = DECIMAL_ONE - self.decimal_x
            self.pixel_w = self.image_info.width - self.pixel_x
            logger.info('decimal_w adjusted to: %s', self.decimal_w)
            logger.info('pixel_w adjusted to: %d', self.pixel_w)
        if (self.decimal_y + self.decimal_h) > DECIMAL_ONE:
            self.decimal_h = DECIMAL_ONE - self.decimal_y
            self.pixel_h = self.image_info.height - self.pixel_y
            logger.info('decimal_h adjusted to: %s', self.decimal_h)
            logger.debug('pixel_h adjusted to: %s', self.pixel_h)

    def _check_for_oob_errors(self):
        if any(axis < 0 for axis in (self.pixel_x, self.pixel_y)):
            raise RequestException(
                "x and y region parameters must be 0 or greater (%s)." %
                self.uri_value
            )
        if self.decimal_x >= DECIMAL_ONE:
            raise RequestException(
                "Region x parameter is greater than the width of the image. "
                "Image width is %d" % self.image_info.width
            )
        if self.decimal_y >= DECIMAL_ONE:
            raise RequestException(
                "Region y parameter is greater than the height of the image. "
                "Image height is %d" % self.image_info.height
            )

    def _populate_slots_for_full(self):
        self.canonical_uri_value = FULL_MODE
        self.pixel_x = 0
        self.decimal_x = 0
        self.pixel_y = 0
        self.decimal_y = 0
        self.pixel_w = self.image_info.width
        self.decimal_w = DECIMAL_ONE
        self.pixel_h = self.image_info.height
        self.decimal_h = DECIMAL_ONE

    def _populate_slots_from_pct(self):
        '''
        Raises:
            SyntaxException
            RequestException
        '''
        # we convert these to pixels and update uri_value
        dimensions = [float(x) for x in self.uri_value.split(':')[1].split(',')]

        if len(dimensions) != 4:
            raise SyntaxException("Exactly (4) coordinates must be supplied.")
        if any(n > 100.0 for n in dimensions):
            raise RequestException(
                "Region percentages must be less than or equal to 100."
            )
        if any((n <= 0) for n in dimensions[2:]):
            raise RequestException(
                "Width and Height Percentages must be greater than 0."
            )

        # decimals
        self.decimal_x, self.decimal_y, self.decimal_w, \
            self.decimal_h = [RegionParameter._pct_to_decimal(d) for d in dimensions]

        # pixels
        self.pixel_x = int(floor(self.decimal_x * self.image_info.width))
        self.pixel_y = int(floor(self.decimal_y * self.image_info.height))
        self.pixel_w = int(floor(self.decimal_w * self.image_info.width))
        self.pixel_h = int(floor(self.decimal_h * self.image_info.height))

    def _populate_slots_for_square(self):
        '''
        Raises:
            RequestException
            SyntaxException
        '''
        #dimensions must be ints, for passing to _populate_slots_from_pixels
        if self.image_info.width > self.image_info.height:
            offset = (self.image_info.width - self.image_info.height) // 2
            dimensions = (offset, 0, self.image_info.height, self.image_info.height)
        else:
            offset = (self.image_info.height - self.image_info.width) // 2
            dimensions = (0, offset, self.image_info.width, self.image_info.width)
        return self._populate_slots_from_pixels(dimensions)

    def _pixel_dims_to_ints(self):
        dimensions = [int(d) for d in self.uri_value.split(',')]
        if any(n <= 0 for n in dimensions[2:]):
            raise RequestException("Width and height must be greater than 0.")
        if len(dimensions) != 4:
            raise SyntaxException("Exactly (4) coordinates must be supplied.")
        return dimensions

    def _populate_slots_from_pixels(self, dimensions):
        # pixels
        self.pixel_x, self.pixel_y, self.pixel_w, self.pixel_h = dimensions
        # decimals
        self.decimal_x = Decimal(self.pixel_x) / Decimal(str(self.image_info.width))
        self.decimal_y = Decimal(self.pixel_y) / Decimal(str(self.image_info.height))
        self.decimal_w = Decimal(self.pixel_w) / Decimal(str(self.image_info.width))
        self.decimal_h = Decimal(self.pixel_h) / Decimal(str(self.image_info.height))

    @staticmethod
    def _mode_from_region_segment(region_segment, image_info):
        '''
        Get the mode of the request from the region segment.

        Args:
            region_segment (str)
        Returns:
            PCT_MODE, FULL_MODE, SQUARE_MODE or PIXEL_MODE
        Raises:
            SyntaxException if this can't be determined.
        '''

        if region_segment == FULL_MODE:
            return FULL_MODE
        elif region_segment == SQUARE_MODE:
            return SQUARE_MODE
        else:
            comma_segments = region_segment.split(',')
            if len(comma_segments) == 4 and all([
                    comma_segments[0] == '0',
                    comma_segments[1] == '0',
                    comma_segments[2] == str(image_info.width),
                    comma_segments[3] == str(image_info.height)
                ]):
                return FULL_MODE
            elif all([n.isdigit() for n in comma_segments]):
                return PIXEL_MODE
            elif region_segment.split(':')[0] == 'pct':
                return PCT_MODE
            else:
                raise SyntaxException(
                    "Region syntax %r is not valid." % region_segment
                )

    @staticmethod
    def _pct_to_decimal(n):
        return Decimal(str(n)) / Decimal('100.0')


class SizeParameter(object):
    '''Internal representation of the size slice of an IIIF image URI.

    Slots:
        uri_value (str):
            The region slice of the URI.
        mode (str):
            One of 'full', 'pct', or 'pixel'
        canonical_uri_value (str):
            The uri_value after it has been normalized to the 'w,' form.
        force_aspect (bool):
            True if the aspect ratio of the image should not be preserved.
        w (int):
            The width.
        h (int):
            The height.
    '''
    PCT_MODE_REGEX = re.compile(r'^pct:(?P<percentage>[0-9]+(\.[0-9]+)?)$')
    PIXEL_MODE_REGEX = re.compile(
        r'^(?P<best_fit>!?)(?P<width>[0-9]*),(?P<height>[0-9]*)$'
    )

    __slots__ = ('uri_value','canonical_uri_value','mode','force_aspect','w','h')

    def __init__(self, uri_value, region_parameter):
        '''Parse the URI slice into an object.

        Args:
            uri_value (str):
                The size slice of an IIIF image URI.
            region_parameter (RegionParameter):
                The region parameter of the request.

        Raises:
            SyntaxException
            RequestException
        '''
        self.uri_value = uri_value
        self.mode = SizeParameter.__mode_from_size_segment(self.uri_value)
        logger.debug('Size mode is "%s" (from "%s")', self.mode, uri_value)

        if self.mode == FULL_MODE:
            self.force_aspect = False
            self.w = region_parameter.pixel_w
            self.h = region_parameter.pixel_h
            self.canonical_uri_value = FULL_MODE
        else:
            if self.mode == PCT_MODE:
                self._populate_slots_from_pct(region_parameter)
            elif self.mode == PIXEL_MODE:
                self._populate_slots_from_pixels(region_parameter)
            else:  # pragma: no cover
                assert False, "Unrecognised mode: %r" % self.mode

            if self.force_aspect:
                self.canonical_uri_value = '%d,%d' % (self.w,self.h)
            else:
                self.canonical_uri_value = '%d,' % (self.w,)

            logger.debug('canonical uri_value for size: %s', self.canonical_uri_value)
            logger.debug('w %s', self.w)
            logger.debug('h %s', self.h)
            if any((dim <= 0 and dim != None) for dim in (self.w, self.h)):
                raise RequestException(
                    "Width and height must both be positive numbers."
                )

    def _populate_slots_from_pct(self,region_parameter):
        m = SizeParameter.PCT_MODE_REGEX.match(self.uri_value)
        assert m is not None

        self.force_aspect = False
        pct_decimal = Decimal(m.group('percentage')) * Decimal('0.01')
        logger.debug(pct_decimal <= Decimal(0))
        logger.debug('pct_decimal: %s', pct_decimal)

        if pct_decimal <= Decimal('0'):
            raise RequestException(
                "Percentage supplied is less than 0 (%r)." % self.uri_value
            )

        w_decimal = region_parameter.pixel_w * pct_decimal
        h_decimal = region_parameter.pixel_h * pct_decimal
        logger.debug('w_decimal %s', w_decimal)
        logger.debug('h_decimal %s', h_decimal)
        # handle teeny, tiny requests.
        if 0 < w_decimal < 1:
            self.w = 1
        else:
            self.w = int(w_decimal)
        if 0 < h_decimal < 1:
            self.h = 1
        else:
            self.h = int(h_decimal)

    def _populate_slots_from_pixels(self, region_parameter):
        m = SizeParameter.PIXEL_MODE_REGEX.match(self.uri_value)
        assert m is not None

        best_fit = bool(m.group('best_fit'))
        request_w = m.group('width')
        request_h = m.group('height')

        if (not best_fit) and request_w and (not request_h):
            self.force_aspect = False
            self.w = Decimal(request_w)
            reduce_by = Decimal(request_w) / region_parameter.pixel_w
            self.h = region_parameter.pixel_h * reduce_by

        elif (not best_fit) and (not request_w) and request_h:
            self.force_aspect = False
            self.h = Decimal(request_h)
            reduce_by = Decimal(request_h) / region_parameter.pixel_h
            self.w = region_parameter.pixel_w * reduce_by

        elif best_fit and request_w and request_h:
            self.force_aspect = False

            ratio_w = Decimal(request_w) / region_parameter.pixel_w
            ratio_h = Decimal(request_h) / region_parameter.pixel_h
            ratio = min(ratio_w, ratio_h)
            self.w = region_parameter.pixel_w * ratio
            self.h = region_parameter.pixel_h * ratio

        elif request_w and request_h:
            self.force_aspect = True
            self.w = Decimal(request_w)
            self.h = Decimal(request_h)

        else:  # pragma: no cover
            assert False, "Incomplete size data in URI: %r" % self.uri_value

        if 0 < self.h < DECIMAL_ONE:
            self.h = 1
        else:
            self.h = int(self.h)
        if 0 < self.w < DECIMAL_ONE:
            self.w = 1
        else:
            self.w = int(self.w)

    @staticmethod
    def __mode_from_size_segment(size_segment):
        '''
        Get the mode of the request from the size segment.

        Args:
            size_segment (str)
        Returns:
            PCT_MODE, FULL_MODE, or PIXEL_MODE
        Raises:
            SyntaxException if this can't be determined.
        '''
        if size_segment == 'full':
            return FULL_MODE

        if SizeParameter.PCT_MODE_REGEX.match(size_segment):
            return PCT_MODE

        m = SizeParameter.PIXEL_MODE_REGEX.match(size_segment)
        if m is not None:
            # In best fit mode, we need both width and height to be specified.
            # Otherwise, we need at least one of width or height.
            if (
                (m.group('best_fit') and m.group('width') and m.group('height')) or
                (not m.group('best_fit') and (m.group('width') or m.group('height')))
            ):
                return PIXEL_MODE

        raise SyntaxException("Size syntax %r is not valid." % size_segment)

    def __str__(self):
        return self.uri_value


class RotationParameter(object):
    '''Internal representation of the rotation slice of an IIIF image URI.

    See http://iiif.io/api/image/2.0/#rotation:

       The rotation parameter specifies mirroring and rotation. A leading
       exclamation mark ("!") indicates that the image should be mirrored by
       reflection on the vertical axis before any rotation is applied.
       The numerical value represents the number of degrees of clockwise
       rotation, and may be any floating point number from 0 to 360.

    Slots:
        canonical_uri_value (str)
        mirror (bool)
        rotation (str)
    '''
    ROTATION_REGEX = re.compile(r'^(?P<mirror>!?)(?P<rotation>[\d.]+)$')

    __slots__ = ('canonical_uri_value', 'mirror', 'rotation')

    def __init__(self, uri_value):
        '''Take the uri value, and parse out mirror and rotation values.
        Args:
            uri_value (str): the rotation slice of the request URI.
        Raises:
            SyntaxException:
                If the argument is not a valid rotation slice.
        '''

        match = RotationParameter.ROTATION_REGEX.match(uri_value)

        if not match:
            raise SyntaxException(
                "Rotation parameter %r is not a number" % uri_value
            )

        self.mirror = bool(match.group('mirror'))
        self.rotation = match.group('rotation')

        try:
            self.canonical_uri_value = '%g' % (float(self.rotation),)
        except ValueError:
            raise SyntaxException(
                "Rotation parameter %r is not a floating point number." %
                uri_value
            )

        if self.mirror:
            self.canonical_uri_value = '!%s' % self.canonical_uri_value

        if not 0.0 <= float(self.rotation) <= 360.0:
            raise SyntaxException(
                "Rotation parameter %r is not between 0 and 360." % uri_value
            )

        logger.debug('Canonical rotation parameter is %s', self.canonical_uri_value)
