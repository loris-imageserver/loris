# -*- encoding: utf-8 -*-

from __future__ import absolute_import

import errno
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


def symlink(src, dst):
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
            # Generate a unique ID, and copy `<src>` to the target directory
            # with a temporary name `<dst>.<ID>.tmp`.  Because we're copying
            # across a filesystem boundary, this initial copy may not be
            # atomic.  We intersperse a random UUID so if different processes
            # are copying into `<dst>`, they don't overlap in their tmp copies.
            mole_id = uuid.uuid4()
            tmp_dst = shutil.copyfile(src, '%s.%s.tmp' % (dst, mole_id))

            # Then do an atomic rename onto the new name, and clean up the
            # source image.
            os.rename(tmp_dst, dst)
            os.unlink(src)
        else:
            raise
