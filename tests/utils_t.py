# -*- encoding: utf-8

import errno
import os
import shutil

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
def src(tmpdir):
    path = str(tmpdir.join('src.txt'))
    open(path, 'wb').write(b'hello world')
    return path


@pytest.fixture
def dst(tmpdir):
    return str(tmpdir.join('dst.txt'))


class TestSafeRename:
    """Tests for ``utils.safe_rename()``.

    Note: one key characteristic of ``safe_rename()`` is that copies are
    atomic.  That's not tested here, because I couldn't think of a way to
    easily test that file moves are atomic in Python.

    """

    def test_renames_file_correctly(self, src, dst):
        assert os.path.exists(src)
        assert not os.path.exists(dst)

        utils.safe_rename(src, dst)

        assert not os.path.exists(src)
        assert os.path.exists(dst)
        assert open(dst, 'rb').read() == b'hello world'

    def test_renames_file_across_filesystems_correctly(self, src, dst):
        # For any given test setup, we can't guarantee where filesystem
        # boundaries lie, so we patch ``os.rename`` to throw an error that
        # looks like it's copying across a filesystem.
        message = "Exception thrown in utils_t.py for TestRename"

        copy_of_rename = os.rename

        def side_effect(s, d):
            """This raises an errno.EXDEV if it detects a rename between
            the ``src`` and ``dst`` used in the test, but otherwise proceeds
            as normal.
            """
            if s == src and d == dst:
                raise OSError(errno.EXDEV, message)
            else:
                copy_of_rename(s, d)

        m = mock.Mock(side_effect=side_effect)
        with mock.patch('loris.utils.os.rename', m):
            utils.safe_rename(src, dst)

        assert os.path.exists(dst)
        assert open(dst, 'rb').read() == b'hello world'

    def test_if_error_is_unexpected_then_is_raised(self, src, dst):
        """
        If the error from ``os.rename()`` isn't because we're trying to copy
        across a filesystem boundary, we get an error
        """
        message = "Exception thrown in utils_t.py for TestRename"
        m = mock.Mock(side_effect=OSError(-1, message))
        with mock.patch('loris.utils.os.rename', m):
            with pytest.raises(OSError):
                utils.safe_rename(src, dst)


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
