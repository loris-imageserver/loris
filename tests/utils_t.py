# -*- encoding: utf-8

import os

import mock
import pytest

from loris import utils


class TestMkdirP:

    def test_creates_directory(self, tmpdir):
        path = str(tmpdir.join('test_creates_directory'))
        assert not os.path.exists(path)

        # If we create the directory, it springs into being
        utils.mkdir_p(path)
        assert os.path.exists(path)

        # If we try to create the directory a second time, we don't throw
        # an exception just because it already exists.
        utils.mkdir_p(path)

    def test_if_error_is_unexpected_then_is_raised(self, tmpdir):
        """
        If the error from ``os.makedirs()`` isn't because the directory
        already exists, we get an error.
        """
        path = str(tmpdir.join('test_if_error_is_unexpected_then_is_raised'))

        message = "Exception thrown in utils_t.py for TestMkdirP"

        m = mock.Mock(side_effect=OSError(-1, message))
        with mock.patch('loris.utils.os.makedirs', m):
            with pytest.raises(OSError) as err:
                utils.mkdir_p(path)
