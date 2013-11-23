Installing Dependencies
=======================

These instructions are known to work with Ubuntu 12.04.3. If you have further information, please provide it!

Loris (PIL or Pillow, actually, with the exception of Kakadu) depends on several external libraries that can't be installed with pip, so there are few step that must be carefully followed to get going. Installing the dependencies manually is a good idea anyway because you'll be able to run the tests.

In order from least to most tedious:

 1. Install [Werkzeug](http://goo.gl/3IWJn) (`>=0.8.3`)

 ```
 $ sudo pip install Werkzeug
 ```

 2. Install Kakadu. [Download the appropriate version or Kakadu](http://goo.gl/owJN8) for your system. **You need at least version 7.2 for all feature to work properly.** Unzip and put the files somewhere on your system. The defaults are `/usr/local/lib` for the shared object file (`libkdu_v72R.so`) and `/usr/local/bin` for `kdu_*`. If you do something different you'll need to change the locations in the `transforms.jp2` section of `etc/loris.conf`. `kdu_libs` should point to a directory, `kdu_expand` should point to a file. **Make sure that `kdu_expand` is executable.**

 3. Install Pillow (recommended) or PIL

 PIL or Pillow have to be built/installed **after** Little CMS, so first remove all instances of PIL or Pillow, including, but not limited to, the `python-imaging` package:

 ```
 sudo pip uninstall PIL
 sudo pip uninstall Pillow
 sudo apt-get purge python-imaging
 ``` 

 Then, get install all of the dependencies (same for PIL or Pillow): 

 ```
 sudo apt-get install libjpeg-turbo8 libjpeg-turbo8-dev libfreetype6 \
 libfreetype6-dev zlib1g-dev liblcms liblcms-dev liblcms-utils libtiff5-dev
 ``` 

 Link them the dirs where PIL or Pillow will find them (this is unfortunate): 

 ```
 sudo ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
 sudo ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/
 sudo ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/
 sudo ln -s /usr/lib/`uname -i`-linux-gnu/liblcms.so /usr/lib/
 sudo ln -s /usr/lib/`uname -i`-linux-gnu/libtiff.so /usr/lib/
 ``` 

 Now do A (Pillow) or B (PIL):

 A. Pillow (recommended)

 ```
 pip install Pillow
 ```

 The output MUST include these lines: 

 ```
 [...]
 --- ZLIB (PNG/ZIP) support available
 --- TIFF G3/G4 (experimental) support available
 --- FREETYPE2 support available
 --- LITTLECMS support available
 [...]
 ```

 B. PIL

 Download the PIL source: 
 
 ```
 cd /tmp
 wget http://effbot.org/downloads/Imaging-1.1.7.tar.gz
 cd Imaging-1.1.7
 ```
 
 Do a test build:
 
 ```
 python setup.py build_ext -i
 python selftest.py
 ``` 

 The output MUST include these lines: 

 ```
 --- PIL CORE support ok
 --- JPEG support ok
 --- ZLIB (PNG/ZIP) support ok
 --- FREETYPE2 support ok
 --- LITTLECMS support ok
 ``` 

 See the README for what to do if there's trouble, otherwise, do: 

 ```
 sudo python setup.py install
 ``` 

 And you should be all set.

Once you done all of this, go ahead and run the tests. From the `loris` directory (not `loris/loris`) run `./test.py`

* * *

Proceed to set [Configuration Options](configuration.md) or go [Back to README](../README.md)
