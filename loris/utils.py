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
