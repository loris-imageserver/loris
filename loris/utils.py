# -*- encoding: utf-8 -*-

from __future__ import absolute_import

import errno
import glob
import logging
import os
import shutil
import uuid


logger = logging.getLogger(__name__)


def mkdir_p(path):
    """Create a directory if it doesn't already exist."""
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            pass
        else:
            raise


def symlink(src, dst, force=True):
    """Create a symlink from ``src`` to ``dst``.

    Creates any required intermediate directories, and overrides any existing
    file at ``dst``.

    """
    if src == dst:
        logger.warn(
            'Circular symlink requested from %s to %s; not creating symlink',
            src, dst)
        return

    mkdir_p(os.path.dirname(dst))

    # Shouldn't be the case, but helps with debugging.
    if os.path.lexists(dst):
        os.unlink(dst)

    os.symlink(src, dst)


def remove_f(path):
    """Remove a file at ``path``, but don't error if it doesn't exist."""
    try:
        os.remove(path)
    except OSError as err:
        if err.errno == errno.ENOENT:
            pass
        else:
            raise


def safe_rename(src, dst):
    """Rename a file from ``src`` to ``dst``.

    We use a custom version rather than the standard library because we
    have two requirements:

    *   Moves must be atomic.  Otherwise Loris may serve a partial image from
        a cache, which causes an error.  ``shutil.move()`` is not atomic.

        Note that multiple threads may try to write to the cache at once,
        so atomicity is required to ensure the serving on one thread doesn't
        pick up a partially saved image from another thread.

    *   Moves must work across filesystems.  Often temp directories and the
        cache directories live on different filesystems.  ``os.rename()`` can
        throw errors if run across filesystems.

    So we try ``os.rename()``, but if we detect a cross-filesystem copy, we
    switch to ``shutil.move()`` with some wrappers to make it atomic.
    """
    logger.debug('Renaming %r to %r', src, dst)
    try:
        os.rename(src, dst)
    except OSError as err:
        logger.debug('Calling os.rename(%r, %r) failed with %r', src, dst, err)
        if err.errno == errno.EXDEV:

            # This is based on the safe, atomic file copying algorithm
            # described in https://stackoverflow.com/a/28090883/1558022.
            #
            # We're assuming that ``src`` is a temporary file in a unique
            # location.  Multiple threads may try to write the same file
            # to ``dst``, but we're the only thread that may be interacting
            # with ``src``.  So we don't need to worry about it disappearing
            # under our feet.

            # First, generate a unique ID, and copy `<src>` to the target
            # directory with a temporary name `<dst>.<ID>.tmp`.  Because we're
            # copying across a filesystem boundary, this may not be atomic.
            mole_id = uuid.uuid4()
            tmp_dst = shutil.copyfile(src, '%s.%s.tmp' % (dst, mole_id))

            # Now we rename the copy (atomically) to `<dst>.<ID>.mole.tmp`.
            # Files within the same directory should be on the same filesystem.
            mole_dst = '%s.%s.mole.tmp' % (dst, mole_id)
            os.rename(tmp_dst, mole_dst)

            # At this point, any files name `<dst>.<ID>.mole.tmp` are complete
            # copies of the source file.  Pick the lowest mole.  If that's
            # not the one we just created, delete ours.
            matching = sorted(glob.glob('dst.*.mole.tmp'))
            if mole_dst != matching[0]:
                remove_f(mole_dst)

            mole_dst = matching[0]

            # If ``dst`` exists, another process has beaten us.  Clean up
            # our mole and the source file.
            if os.path.exists(dst):
                remove_f(mole_dst)
                os.unlink(src)
                return

            # Otherwise, rename the temporary file to its final name.  Don't
            # worry if it's already gone -- it just means another process
            # did it first.
            try:
                os.rename(mole_dst, dst)
            except OSError as err:
                if err.errno == errno.ENOENT:
                    pass
                else:
                    raise

            os.unlink(src)
        else:
            raise
