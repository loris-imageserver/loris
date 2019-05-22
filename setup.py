#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import loris
import os


VERSION = loris.__version__


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


# We use requirements.txt so we can provide a deterministic set of packages
# to be installed, not the latest version that happens to be available.
# e.g. Pillow 5 has some issues with TIFF files that we care about.
with open('requirements.txt') as f:
    install_requires = list(f)


def _read(fname):
    return open(local_file(fname)).read()


setup(
    name='Loris',
    author='Jon Stroop',
    author_email='jpstroop@gmail.com',
    url='https://github.com/loris-imageserver/loris',
    description = ('IIIF Image API 2.0 Level 2 compliant Image Server'),
    long_description=_read('README.md'),
    license='Simplified BSD',
    version=VERSION,
    packages=['loris'],
    install_requires=install_requires,
)

