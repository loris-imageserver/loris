# -*- encoding: utf-8 -*-

from __future__ import absolute_import

import errno
import logging
import os


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


def rename(src, dst):
    """Rename a file from ``src`` to ``dst``.

    We use a custom version rather than the standard library because we
    have two requirements:

    *   Moves must be atomic.  Otherwise Loris may serve a partial image from
        a cache, which causes an error.  ``shutil.move()`` is not atomic.
    *   Moves must work across filesystems.  Often temp directories and the
        cache directories live on different filesystems.  ``os.rename()`` can
        throw errors if run across filesystems.

    So we try ``os.rename()``, but if we detect a cross-filesystem copy, we
    switch to ``shutil.move()`` with some wrappers to make it atomic.
    """
    os.rename(src, dst)
