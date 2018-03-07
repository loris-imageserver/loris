# -*- encoding: utf-8 -*-

try:
    from io import BytesIO
except ImportError:  # Python 2
    from StringIO import StringIO as BytesIO

from hypothesis import given
from hypothesis.strategies import binary
import pytest

from loris.jp2_extractor import Dimensions, JP2Extractor, JP2ExtractionError


@pytest.fixture
def extractor():
    return JP2Extractor()



class TestJP2Extractor(object):

    def test_valid_signature_box_is_accepted(self, extractor):
        extractor._check_signature_box(
            BytesIO(b'\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a')
        )

    @pytest.mark.parametrize('signature_box', [
        b'',
        b'notavalidsignaturebox',
        b'\x00' * 12,
    ])
    def test_invalid_signature_box_is_rejected(self, extractor, signature_box):
        with pytest.raises(JP2ExtractionError) as err:
            extractor._check_signature_box(BytesIO(signature_box))
        assert 'Bad signature box' in str(err.value)

    @given(signature_box=binary())
    def test_check_sig_box_is_ok_or_error(self, extractor, signature_box):
        try:
            extractor._check_signature_box(BytesIO(signature_box))
        except JP2ExtractionError as err:
            assert 'Bad signature box' in str(err)

    def test_valid_file_type_box_is_accepted(self, extractor):
        extractor._check_file_type_box(BytesIO(b'\x00\x00\x00\x0cftypjp2\040'))

    @pytest.mark.parametrize('file_type_box, exception_message', [
        # The first four bytes are the length field
        (b'', 'Error reading the length field in the File Type box'),
        (b'\x00\x01', 'Error reading the length field in the File Type box'),

        # After the length header, it looks for 'ftyp'
        (b'\x00\x00\x00\x00FTYP', 'Bad type in the File Type box'),
        (b'\x00\x00\x00\x00____', 'Bad type in the File Type box'),

        # Then it looks for jp2\040
        (b'\x00\x00\x00\x00ftypJP2X', 'Bad brand in the File Type box'),
        (b'\x00\x00\x00\x00ftyp____', 'Bad brand in the File Type box'),
    ])
    def test_bad_file_type_box_is_rejected(
        self, extractor, file_type_box, exception_message
    ):
        with pytest.raises(JP2ExtractionError) as err:
            extractor._check_file_type_box(BytesIO(file_type_box))
        assert exception_message in str(err.value)

    @pytest.mark.parametrize('file_type_box', [
        # Here we have length 20, so we read four extra bytes from the endf
        # of the string.
        b'\x00\x00\x00\x14ftypjp2\040\x00\x00\x00\x00XXXXYYYY',

        # Here we have length 16, so we don't read any extra bytes.
        b'\x00\x00\x00\x10ftypjp2\040\x00\x00\x00\x00YYYY',

        # Here we have length 8 (too short!), make sure we don't do anything
        # silly to read extra bytes.
        b'\x00\x00\x00\x08ftypjp2\040\x00\x00\x00\x00YYYY',
    ])
    def test_reads_to_end_of_file_type_box_with_length(
        self, extractor, file_type_box
    ):
        """
        If a valid length is supplied for the file type box, we correctly
        read to the end of it before returning.
        """
        b = BytesIO(file_type_box)
        extractor._check_file_type_box(b)

        assert b.read(4) == b'YYYY'

    def test_skips_end_of_file_type_box_without_length(self, extractor):
        # If the file type box doesn't have a known length, we don't read
        # beyond the bytes we know are part of the box.
        b = BytesIO(b'\x00\x00\x00\x00ftypjp2\040\x00\x00\x00\x00XXXX')
        extractor._check_file_type_box(b)

        assert b.read(4) == b'XXXX'

    @given(file_type_box=binary())
    def test_file_type_box_is_ok_or_error(self, extractor, file_type_box):
        try:
            extractor._check_file_type_box(BytesIO(file_type_box))
        except JP2ExtractionError as err:
            assert 'File Type box' in str(err)

    @pytest.mark.parametrize('header_box_bytes, expected_dimensions', [
        (
            b'\x00\x00\x00\x01\x00\x00\x00\x01',
            Dimensions(height=1, width=1)
        ),
        (
            b'\x00\x00\x00\x11\x00\x00\x00\x00',
            Dimensions(height=17, width=0)
        ),
        (
            b'\x00\x00\x00\x00\x00\x00\x00\x11',
            Dimensions(height=0, width=17)
        ),
        (
            b'\x01\x01\x01\x01\x02\x02\x02\x02',
            Dimensions(height=16843009, width=33686018)
        ),
    ])
    def test_reading_dimensions_from_headr_box(
        self, extractor, header_box_bytes, expected_dimensions
    ):
        b = BytesIO(b'\x00\x00\x00\x16ihdr' + header_box_bytes)
        dimensions = extractor._get_dimensions_from_image_header_box(b)
        assert dimensions == expected_dimensions

    @pytest.mark.parametrize('image_header_box, exception_message', [
        # The first four bytes are the length field
        (b'', 'Error reading the length field in the Image Header box'),
        (b'\x00', 'Error reading the length field in the Image Header box'),

        # The length of the Image Header field should always be 22
        (b'\x00\x00\x00\x00', 'Incorrect length in the Image Header box'),
        (b'\x00\x00\x01\x01', 'Incorrect length in the Image Header box'),
        (b'\xff\xff\xff\xff', 'Incorrect length in the Image Header box'),

        # After the length header, it looks for 'ihdr'
        (b'\x00\x00\x00\x16IHDR', 'Bad type in the Image Header box'),
        (b'\x00\x00\x00\x16____', 'Bad type in the Image Header box'),

        # After the length and type, not enough data for dimensions
        (b'\x00\x00\x00\x16ihdr\x00',
         'Error parsing dimensions in the Image Header box'),
        (b'\x00\x00\x00\x16ihdr\x00\x00\x00\x00\x01\x01',
         'Error parsing dimensions in the Image Header box'),
    ])
    def test_bad_image_header_box_is_rejected(
        self, extractor, image_header_box, exception_message
    ):
        with pytest.raises(JP2ExtractionError) as err:
            b = BytesIO(image_header_box)
            extractor._get_dimensions_from_image_header_box(b)
        assert exception_message in str(err.value)

    @given(image_header_box=binary())
    def test_image_header_box_is_okay_or_error(
        self, extractor, image_header_box
    ):
        try:
            dimensions = extractor._get_dimensions_from_image_header_box(
                BytesIO(image_header_box)
            )
        except JP2ExtractionError as err:
            assert 'Image Header box' in str(err)
        else:
            assert isinstance(dimensions, tuple)
            assert len(dimensions) == 2
            assert all(isinstance(i, int) for i in tuple)

    @pytest.mark.parametrize('colour_specification_box, exception_message', [
        # The first four bytes are the length field
        (b'', 'Error reading the length field in the Colour Specification box'),
        (b'\x00', 'Error reading the length field in the Colour Specification box'),

        # After the length header, it looks for 'colr'
        (b'\x00\x00\x00\x16COLR', 'Bad type in the Colour Specification box'),
        (b'\x00\x00\x00\x16____', 'Bad type in the Colour Specification box'),
    ])
    def test_bad_colour_specification_box_is_rejected(
        self, extractor, colour_specification_box, exception_message
    ):
        with pytest.raises(JP2ExtractionError) as err:
            b = BytesIO(colour_specification_box)
            extractor._parse_colour_specification_box(b)
        assert exception_message in str(err.value)

    @pytest.mark.parametrize('colour_specification_box, expected_result', [
        # METH = 1 and EnumCS = 16
        (b'\x00\x00\x00\x16colr\x01\x00\x00\x00\x00\x00\x10',
         (['gray', 'color'], None)),

        # METH = 1 and EnumCS = 17
        (b'\x00\x00\x00\x16colr\x01\x00\x00\x00\x00\x00\x11',
         (['gray'], None)),

        # METH = 1 and EnumCS = 18
        (b'\x00\x00\x00\x16colr\x01\x00\x00\x00\x00\x00\x12',
         ([], None)),

        # METH = 2, with an eight-byte ICC profile
        (b'\x00\x00\x00\x16colr\x02\x00\x00\x00\x00\x00\x08\x01\x02\x03\x03',
         (['gray', 'color'], b'\x00\x00\x00\x08\x01\x02\x03\x03')),
    ])
    def test_parsing_color_specification_box(
        self, extractor, colour_specification_box, expected_result
    ):
        b = BytesIO(colour_specification_box)
        assert extractor._parse_colour_specification_box(b) == expected_result

    @pytest.mark.parametrize('meth_value', [b'\x00', b'\xff'])
    def test_illegal_meth_is_not_error(self, extractor, meth_value):
        """
        The only legal values of METH are 1 and 2; if that's not correct,
        check we don't throw an exception.
        """
        b = BytesIO(b'\x00\x00\x00\x16colr' + meth_value)
        assert extractor._parse_colour_specification_box(b) == ([], None)

    @pytest.mark.parametrize('prec_value', [b'\x00', b'\x01', b'\xff'])
    @pytest.mark.parametrize('approx_value', [b'\x00', b'\x01', b'\xff'])
    def test_illegal_prec_approx_is_not_error(
        self, extractor, prec_value, approx_value
    ):
        """
        The spec says that both PREC and APPROX should be zero, but we
        should ignore these fields.  Check we don't throw an exception on
        non-zero values.
        """
        b = BytesIO(
            b'\x00\x00\x00\x16colr\x01' +
            prec_value + approx_value + b'\x00\x00\x00\x10')
        extractor._parse_colour_specification_box(b)

    @pytest.mark.parametrize('enumcs_value', [
        b'\x00\x00\x00\x00',
        b'\x00\x00\x00\x13',
        b'\xff\xff\xff\xff',
    ])
    def test_illegal_enumcs_is_not_error(self, extractor, enumcs_value):
        """
        The spec tells us that there are three legal values for EnumCS:
        16, 17 and 18.  Check we don't throw an exception if we get an
        unrecognised value.
        """
        b = BytesIO(b'\x00\x00\x00\x16colr\x01\x00\x00' + enumcs_value)
        assert extractor._parse_colour_specification_box(b) == ([], None)

    @given(colour_specification_box=binary())
    def test_parse_colour_specification_box_is_okay_or_error(
        self, extractor, colour_specification_box
    ):
        try:
            result = extractor._parse_colour_specification_box(
                BytesIO(colour_specification_box)
            )
        except JP2ExtractionError as err:
            assert 'Colour Specification box' in str(err)
        else:
            assert isinstance(result, tuple)
            assert len(result) == 2
            qualities, profile_bytes = result
            assert isinstance(qualities, list)
            assert isinstance(profile_bytes, bytes)

    @pytest.mark.parametrize('marker_code', [b'\xFF\x52', b'\xFE\x52', b'00'])
    def test_bad_siz_marker_code_is_error(self, extractor, marker_code):
        jp2 = BytesIO(marker_code)
        with pytest.raises(JP2ExtractionError) as err:
            extractor._parse_siz_marker_segment(jp2)
        assert 'Bad marker code in the SIZ marker segment' in str(err.value)
