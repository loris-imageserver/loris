# -*- encoding: utf-8 -*-

try:
    from io import BytesIO
except ImportError:  # Python 2
    from StringIO import StringIO as BytesIO

from hypothesis import given
from hypothesis.strategies import binary
import pytest

from loris.jp2_extractor import JP2Extractor, JP2ExtractionError


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
        assert 'Bad signature box' in err.value.message

    @given(signature_box=binary())
    def test_check_sig_box_is_ok_or_error(self, extractor, signature_box):
        try:
            extractor._check_signature_box(BytesIO(signature_box))
        except JP2ExtractionError as err:
            assert 'Bad signature box' in err.message

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
        assert exception_message in err.value.message

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
            assert 'File Type box' in err.message

    @pytest.mark.parametrize('header_box_bytes, expected_dimensions', [
        (b'\x00\x00\x00\x01\x00\x00\x00\x01', (1, 1)),
        (b'\x00\x00\x00\x11\x00\x00\x00\x00', (17, 0)),
        (b'\x00\x00\x00\x00\x00\x00\x00\x11', (0, 17)),
        (b'\x01\x01\x01\x01\x02\x02\x02\x02', (16843009, 33686018)),
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
        assert exception_message in err.value.message

    @given(image_header_box=binary())
    def test_image_header_box_is_okay_or_error(
        self, extractor, image_header_box
    ):
        try:
            dimensions = extractor._get_dimensions_from_image_header_box(
                BytesIO(image_header_box)
            )
        except JP2ExtractionError as err:
            assert 'Image Header box' in err.message
        else:
            assert isinstance(dimensions, tuple)
            assert len(dimensions) == 2
            assert all(isinstance(i, int) for i in tuple)
