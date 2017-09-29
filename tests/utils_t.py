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
            with pytest.raises(OSError):
                utils.mkdir_p(path)


@pytest.fixture
def symlink_src(tmpdir):
    path = str(tmpdir.join('symlink_src'))
    open(path, 'wb').write(b'I am a symlink')
    yield path
    os.unlink(path)


class TestSymlink:

    @staticmethod
    def _assert_is_symlink(src, dst):
        assert os.path.exists(dst)
        assert os.path.islink(dst)
        assert os.path.realpath(dst) == src

    def test_creates_symlink(self, symlink_src, tmpdir):
        dst = str(tmpdir.join('foo'))
        utils.symlink(symlink_src, dst)
        self._assert_is_symlink(symlink_src, dst)

    def test_creates_intermediate_directories(self, symlink_src, tmpdir):
        dst = str(tmpdir.join('foo/bar/baz'))
        utils.symlink(symlink_src, dst)
        self._assert_is_symlink(symlink_src, dst)

    def test_circular_symlink_is_ignored(self, symlink_src):
        utils.symlink(symlink_src, symlink_src)
        assert os.path.isfile(symlink_src)

    def test_old_symlink_is_replaced(self, symlink_src, tmpdir):
        # Create the dst, and write some text into it
        dst = str(tmpdir.join('foo'))
        open(dst, 'wb').write(b'I am the old file')

        # Now create a symlink to dst, and check it's become a symlink, and
        # the old contents are gone
        utils.symlink(symlink_src, dst)
        self._assert_is_symlink(symlink_src, dst)
        assert open(dst, 'wb') != b'I am the old file'
