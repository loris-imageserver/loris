# -*- encoding: utf-8
"""
Implements a parser for JPEG2000 images.

We don't use Pillow for JPEG2000, because it doesn't expose advanced
features such as tiles or color profiles.

Where appropriate, references are to ISO/IEC 15444-1:2000(E).

"""

import collections
from collections import deque
import logging
import os
import struct

from loris.loris_exception import LorisException

logger = logging.getLogger(__name__)


class JP2ExtractionError(LorisException):
    """Raised for errors when extracting data from a JP2 image."""
    pass


def _parse_length(jp2, box_name):
    """
    Internally, a JP2 is a series of boxes.  Within each box,
    the first 4 bytes are a length field, measuring the size of the box
    (including the length field itself).

    If ``jp2`` is at the start of a box, return the length of the next box.

    See § I.4.

    """
    length_field = jp2.read(4)
    try:
        return struct.unpack('>I', length_field)[0]
    except struct.error as err:
        raise JP2ExtractionError(
            "Error reading the length field in the %s box: %r" %
            (box_name, err)
        )


def _read_jp2_until_match(jp2, match):
    """
    Continue to read bytes from ``jp2`` until ``match`` is encountered,
    at which point rewind so the stream starts just before ``match``.
    """
    window = collections.deque([], len(match))
    while b''.join(window) != match:
        b = jp2.read(1)
        c = struct.unpack('c', b)[0]
        window.append(c)

    jp2.seek(-len(match), os.SEEK_CUR)


class JP2Extractor(object):
    """
    Contains logic for parsing a JPEG2000 images.

    This class is meant to be used as a mixin on ImageInfo, but is kept
    separately for easier testing.
    """
    __slots__ = ()

    def _check_signature_box(self, jp2):
        """
        The first 12 bytes of a JP2 file are the "JPEG 2000 Signature box".
        Quoting ISO/IEC 15444-1:2000(E) § I.5.1:

            For file verification purposes, this box can be considered a
            fixed-length 12-byte string which shall have the value:
            0x0000 000C 6A50 2020 0D0A 870A.

        """
        signature = jp2.read(12)
        if signature != b'\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a':
            raise JP2ExtractionError("Bad signature box: %r" % signature)

    def _check_file_type_box(self, jp2):
        """
        After the Signature box is the "File Type box" (see § I.5.2).
        This is a variable length box, laid out as follows:

            0 - 3   Length
            4 - 7   Type, which must be 'ftyp' (0x6674 7970)
            8 - 11  Brand, the only allowed value of which is 'jp2\040'
            12+     Minor version of the JP2 spec; compatibility list for other
                    standards.  This is a variable length field which we don't
                    need to worry about.

        """
        # We should probably check the length is valid; in practice we don't
        # right now.
        file_type_box_length = _parse_length(jp2, 'File Type')

        file_type = jp2.read(4)
        if file_type != b'ftyp':
            raise JP2ExtractionError(
                "Bad type in the File Type box: %r" % file_type
            )

        file_brand = jp2.read(4)
        if file_brand != b'jp2\040':
            raise JP2ExtractionError(
                "Bad brand in the File Type box: %r" % file_brand
            )

        # After the brand comes the minor version.  We don't care about the
        # value of this field (it should always be zero, and the spec says to
        # carry on even if it's not), so just discard those bytes at once.
        jp2.read(4)

        # We've already consumed 16 bytes of the box reading the length, type,
        # and brand fields.  If we know the length, we consume any remaining
        # bytes in this box before returning.
        if file_type_box_length > 0:
            jp2.read(max(file_type_box_length - 16, 0))

    def _get_dimensions_from_image_header_box(self, jp2):
        """
        The Image Header box contains "fixed length generic information
        about the image".  It is 22 bytes long, laid out as follows:

            0 - 3   Length (which is always 22)
            4 - 7   Type, which must be 'ihdr' (0x6968 6472)
            8 - 11  Image area height, stored as a 4-byte big endian uint
            12 - 15 Image area width, stored as a 4-byte big endian uint
            16 - 21 Other fields we don't care about

        Starting at the beginning of the Image Header box, this method parses
        the header and returns a tuple (height, width).

        See § I.5.3.1 for details.
        """
        header_box_length = _parse_length(jp2, 'Image Header')
        if header_box_length != 22:
            raise JP2ExtractionError(
                "Incorrect length in the Image Header box: %r" %
                header_box_length
            )

        header_box_type = jp2.read(4)
        if header_box_type != b'ihdr':
            raise JP2ExtractionError(
                "Bad type in the Image Header box: %r" % header_box_type
            )

        height_bytes = jp2.read(4)
        width_bytes = jp2.read(4)

        try:
            height = struct.unpack('>I', height_bytes)[0]
            width = struct.unpack('>I', width_bytes)[0]
        except struct.error as err:
            raise JP2ExtractionError(
                "Error parsing dimensions in the Image Header box: %s (%r, %r)"
                % (err, height_bytes, width_bytes)
            )

        # We've already consumed 16 bytes of the box reading the length, type,
        # height and width.  Consume the rest of the box before returning.
        jp2.read(22 - 16)

        return (height, width)

    def extract_jp2(self, jp2):
        """
        Given a file-like object that contains a JP2 image, attempt
        to parse the JP2 data and store width, height and other attributes
        on the instance.
        """
        # Check that the first two boxes (the Signature box and the File Type
        # box) are both correct.
        self._check_signature_box(jp2)
        self._check_file_type_box(jp2)

        # After the File Type box comes the JP2 header box.  Quoting § I.5.3:
        #
        #   The JP2 Header box may be located anywhere within the file after
        #   the File Type box but before the Contiguous Codestream box.
        #
        # This is a superbox containing other boxes which contain (among other
        # things) information about the dimensions and color space of
        # the image.  The type of this box is 'jp2h'.
        _read_jp2_until_match(jp2, b'jp2h')
        jp2.read(4)

        # The first box is the Image Header box, which is *always* the first
        # box in the JP2 Header box (see § I.5.3).  In particular, it gives
        # us the height and the width.
        dimensions = self._get_dimensions_from_image_header_box(jp2)
        self.height, self.width = dimensions
        logger.debug("width:  %d", self.width)
        logger.debug("height: %d", self.height)

        scaleFactors = []

        # Figure out color or grayscale.
        # Depending color profiles; there's probably a better way (or more than
        # one, anyway.)
        # see: JP2 I.5.3.3 Colour Specification box
        window = collections.deque([], 4)
        while ''.join(window) != 'colr':
            b = jp2.read(1)
            c = struct.unpack('c', b)[0]
            window.append(c)

        colr_meth = struct.unpack('B', jp2.read(1))[0]
        logger.debug('colr METH: %d', colr_meth)

        # PREC and APPROX, 1 byte each
        colr_prec = struct.unpack('b', jp2.read(1))[0]
        colr_approx = struct.unpack('B', jp2.read(1))[0]
        logger.debug('colr PREC: %d', colr_prec)
        logger.debug('colr APPROX: %d', colr_approx)

        if colr_meth == 1: # Enumerated Colourspace
            self.color_profile_bytes = None
            enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
            logger.debug('Image contains an enumerated colourspace: %d', enum_cs)
            logger.debug('Enumerated colourspace: %d', enum_cs)
            if enum_cs == 16: # sRGB
                self.profile.description['qualities'] += ['gray', 'color']
            elif enum_cs == 17: # grayscale
                self.profile.description['qualities'] += ['gray']
            elif enum_cs == 18: # sYCC
                pass
            else:
                msg =  'Enumerated colourspace is neither "16", "17", or "18". '
                msg += 'See jp2 spec pg. 139.'
                logger.warn(msg)
        elif colr_meth == 2:
            # (Restricted ICC profile).
            logger.debug('Image contains a restricted, embedded colour profile')
            # see http://www.color.org/icc-1_1998-09.pdf, page 18.
            self.assign_color_profile(jp2)
        else:
            logger.warn('colr METH is neither "1" or "2". See jp2 spec pg. 139.')

            # colr METH 3 = Any ICC method, colr METH 4 = Vendor Colour method
            # See jp2 spec pg. 182 -  Table M.24 (Color spec box legal values)
            if colr_meth <= 4 and -128 <= colr_prec <= 127 and 1 <= colr_approx <= 4:
                self.assign_color_profile(jp2)

        logger.debug('qualities: %s', self.profile.description['qualities'])

        window =  deque(jp2.read(2), 2)
        # start of codestream
        while map(ord, window) != [0xFF, 0x4F]: # (SOC - required, see pg 14)
            window.append(jp2.read(1))
        while map(ord, window) != [0xFF, 0x51]:  # (SIZ  - required, see pg 14)
            window.append(jp2.read(1))
        jp2.read(20) # through Lsiz (16), Rsiz (16), Xsiz (32), Ysiz (32), XOsiz (32), YOsiz (32)
        tile_width = int(struct.unpack(">I", jp2.read(4))[0]) # XTsiz (32)
        tile_height = int(struct.unpack(">I", jp2.read(4))[0]) # YTsiz (32)
        logger.debug("tile width: %s", tile_width)
        logger.debug("tile height: %s", tile_height)
        self.tiles.append( { 'width' : tile_width } )
        if tile_width != tile_height:
            self.tiles[0]['height'] = tile_height
        jp2.read(10) # XTOsiz (32), YTOsiz (32), Csiz (16)

        window =  deque(jp2.read(2), 2)
        # while (ord(b) != 0xFF): b = jp2.read(1)
        # b = jp2.read(1) # 0x52: The COD marker segment
        while map(ord, window) != [0xFF, 0x52]:  # (COD - required, see pg 14)
            window.append(jp2.read(1))

        jp2.read(7) # through Lcod (16), Scod (8), SGcod (32)
        levels = int(struct.unpack(">B", jp2.read(1))[0])
        logger.debug("levels: %s", levels)
        scaleFactors = [pow(2, l) for l in range(0,levels+1)]
        self.tiles[0]['scaleFactors'] = scaleFactors
        jp2.read(4) # through code block stuff

        # We may have precincts if Scod or Scoc = xxxx xxx0
        # But we don't need to examine as this is the last variable in the
        # COD segment. Instead check if the next byte == 0xFF. If it is,
        # we don't have a Precint size parameter and we've moved on to either
        # the COC (optional, marker = 0xFF53) or the QCD (required,
        # marker = 0xFF5C)
        b = jp2.read(1)
        if ord(b) != 0xFF:
            if self.tiles[0]['width'] == self.width \
                and self.tiles[0].get('height') in (self.height, None):
                # Clear what we got above in SIZ and prefer this. This could
                # technically break as it's possible to have precincts inside tiles.
                # Let's wait for that to come up....
                self.tiles = []

                for level in range(levels+1):
                    i = int(bin(struct.unpack(">B", b)[0])[2:].zfill(8),2)
                    x = i&15
                    y = i >> 4
                    w = 2**x
                    h = 2**y
                    b = jp2.read(1)
                    try:
                        entry = next((i for i in self.tiles if i['width'] == w))
                        entry['scaleFactors'].append(pow(2, level))
                    except StopIteration:
                        self.tiles.append({'width':w, 'scaleFactors':[pow(2, level)]})

        self.sizes = [
            {'width': width, 'height': height}
            for width, height in self.sizes_for_scales(scaleFactors)
        ]
        self.sizes.sort(key=lambda size: max([size['width'], size['height']]))
