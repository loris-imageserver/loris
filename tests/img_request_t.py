# -*- encoding: utf-8

import pytest

from loris.img_request import ImageRequest


class TestImageRequest(object):

    @pytest.mark.parametrize('args, request_path', [
        (('id1', 'full', 'full', '0', 'default', 'jpg'),
         'id1/full/full/0/default.jpg'),
        (('id2', '100,100,200,200', '200,', '30', 'gray', 'png'),
         'id2/100,100,200,200/200,/30/gray.png'),
    ])
    def test_request_path(self, args, request_path):
        request = ImageRequest(*args)
        assert request.request_path == request_path

    @pytest.mark.parametrize('args, is_canonical', [
        (('id1', 'full', 'full', '0', 'default', 'jpg'), True),
        (('id2', 'full', 'full', '30', 'default', 'jpg'), True),
        (('id3', 'full', '100,20', '30', 'default', 'jpg'), True),

        # This is a best-fit size, so the canonical size parameter is "80,".
        (('id4', 'full', '!80,20', '30', 'default', 'jpg'), False),
    ])
    def test_is_canonical(self, args, is_canonical):
        info = img_info.ImageInfo(None)
        info.width = 100
        info.height = 100
        request = ImageRequest(*args)

        assert request.is_canonical(info) == is_canonical
