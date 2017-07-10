# -*- encoding: utf-8 -*-

import errno
import os


def mkdir_p(path):
    '''Create a directory if it doesn't already exist.'''
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            pass
        else:
            raise
