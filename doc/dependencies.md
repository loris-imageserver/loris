Installing Dependencies
=======================

These instructions are known to work with Ubuntu 12.04 and Ubuntu 14.04. If you have further information, please provide it!

Loris (Pillow, actually, with the exception of Kakadu) depends on several external libraries that can't be installed with pip, so there are few steps that must be carefully followed to get going. Installing the dependencies manually is a good idea anyway because you'll be able to run the tests.

In order from least to most tedious:

 1. Install [Werkzeug](http://goo.gl/3IWJn) (`>=0.8.3`)

         $ sudo pip install werkzeug

 2. Install OpenJPEG or Kakadu for JPEG2000 Support.

    In `/etc/loris2.conf` you'll need to choose either the `KakaduJP2Transformer` or the `OPJ_JP2Transformer`. The former is enabled by default. Read on....

      1. __Kakadu.__ From Version 1.2.2 on, a copies of Kakadu for 64-bit Linux and OS X are included with Loris. These copies may be used, provided you comply with the [terms outlined by NewSouth Innovations](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22). Please see their website or [LICENSE-Kakadu.txt](https://github.com/pulibrary/loris/blob/development/LICENSE-Kakadu.txt) for details. 

        If you are deploying on a different system or architecture, you can [Download the appropriate version of Kakadu](http://goo.gl/owJN8) for your system, if it is available, or else contact Kakadu for a license. **You need at least version 7.0 for all features to work properly.**

        The binaries and shared object file are stored in the source code at `loris/(bin|lib)/$system/$machine` where `$system/$machine` is the response from the following command:

            $ python -c "import platform as p; print '%s/%s' % (p.system(),p.machine())"

	    Meaning that if you would like (or need) to supply your own version you may do so before deployment by putting `kdu_expand` and `libkdu_*` in their appropriate directories.

	    After deployment the files are `/usr/local/(bin|lib)`.


	  2. __OpenJPEG.__ 

	    __OpenJPEG 2.1 or greater is required, and your JP2s _must have tiles (not precincts)_ in order for performance to be anywhere near acceptable.__ Even then, OpenJPEG is generally not as performant as Kakadu with the exception of tile extraction, where it seems to be at least as fast if not faster. Large versions of 'full' images are generally quite slow until cached; thumbnails (120 ~ 300px) are generally OK.

        Copies of OpenJPEG for 64-bit Linux and OS X are included with Loris. The binaries and shared object file are stored in the source code at `loris/(bin|lib)/$system/$machine` where `$system/$machine` is the response from the following command:

            $ python -c "import platform as p; print '%s/%s' % (p.system(),p.machine())"
        
	    If you need a different version, it is fairly easy to compile openjpeg (note that the version available via apt is not new enough at this time.) Download the version appropriate for your system [here](https://code.google.com/p/openjpeg/wiki/Downloads?tm=2), unpack it, and see `INSTALL` for details. You'll need cmake and gcc.

	        $ apt-get install cmake build-essential

 3. Install Pillow

    Pillow's external dependencies have to be built/installed before Pillow is installed, so, to be safe, first remove all instances of PIL or Pillow, including, but not limited to, the `python-imaging` package:

        $ sudo pip uninstall PIL
        $ sudo pip uninstall Pillow
        $ sudo apt-get purge python-imaging

    Then, get install all of the dependencies--note that exact versions may vary depending on your package manager and OS version: 

        $ sudo apt-get install libjpeg-turbo8 libjpeg-turbo8-dev libfreetype6 \
        libfreetype6-dev zlib1g-dev liblcms2-2 liblcms2-dev liblcms-utils \
        libtiff5-dev libwebp-dev python-dev python-setuptools

    If you're planning on using OpenJPEG, it should have been installed in step 2 above.

    Now install Pillow:

        $ pip install Pillow

    The output should (and MUST!) include these lines: 

        [...]
        --- JPEG support available
        --- OPENJPEG (JPEG2000) support available (2.1)
        --- ZLIB (PNG/ZIP) support available
        --- LIBTIFF support available
        --- FREETYPE2 support available
        --- LITTLECMS2 support available
        --- WEBP support available
        --- WEBPMUX support available
        [...]

    The following are required python libraries that must currently exist on the system:

        $ sudo pip install configobj
        $ sudo pip install requests
        $ sudo pip install mock
        $ sudo pip install responses

    Once you done all of this, go ahead and run the tests. From the `loris` directory (not `loris/loris`) run `./test.py`

* * *

Proceed to set [Configuration Options](configuration.md) or go [Back to README](../README.md)
	
