Installing Dependencies
=======================

These instructions are known to work with Ubuntu 14.04 and Ubuntu 16.04. If you have further information, please provide it!

Loris (Pillow, actually, with the exception of Kakadu) depends on several external libraries that can't be installed with pip, so there are few steps that must be carefully followed to get going. Installing the dependencies manually is a good idea if you want to run the tests.

### Install Kakadu for JPEG2000 Support.

From Version 2.0 on, `setup.py` __does not__ install Kakadu. The copies included with the distribution are intended for continuous integration and unit testing. These copies may be used, provided they work in your environment and that you comply with the [terms outlined by NewSouth Innovations](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22). Please see their website or [LICENSE-Kakadu.txt](https://github.com/pulibrary/loris/blob/development/LICENSE-Kakadu.txt) for details.

If you are deploying on a different system or architecture, you can [Download the appropriate version of Kakadu](http://goo.gl/owJN8) for your system, if it is available, or else contact Kakadu for a license. **You need at least version 7.0 for all features to work properly.**

### Install `pip` and `setuptools`

[`pip`](https://pip.pypa.io/en/latest/index.html) is used to install dependencies; [`setuptools`](https://pypi.python.org/pypi/setuptools) is used to install Loris.

    $ sudo apt-get install python-pip python-setuptools

### Install Pillow

Pillow's external dependencies __MUST__ be built/installed before Pillow is installed, so, to be safe, first remove all instances of PIL or Pillow, including, but not limited to, the `python-imaging` package:

    $ sudo pip uninstall PIL
    $ sudo pip uninstall Pillow
    $ sudo apt-get purge python-imaging

Then, install all of the dependencies--note that exact versions may vary depending on your package manager and OS version:

    $ sudo apt-get install libjpeg-turbo8-dev libfreetype6-dev zlib1g-dev \
    liblcms2-dev liblcms2-utils libtiff5-dev python-dev libwebp-dev apache2 \
    libapache2-mod-wsgi

Now install Pillow (setup.py would do this for you, but it's better to do separately and check):

    $ sudo pip install Pillow

In case you plan on working on the source code without running setup.py, the following are required python libraries that must currently exist in your Python environment:

    $ sudo pip install configobj
    $ sudo pip install requests
    $ sudo pip install mock
    $ sudo pip install responses


* * *

Proceed to set [Configuration Options](configuration.md) or go [Back to README](../README.md)
