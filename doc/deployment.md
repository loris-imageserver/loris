Deployment
==========

This is still in progress, but should give you the gist. Additions/corrections
welcome.

Install and Test Utility Dependencies
-------------------------------------

### ImageMagick
Install [ImageMagick] [1]

Call `convert -v`

You should see something like this:

```
  Version: ImageMagick 6.6.9-7 2012-08-17 Q16 http://www.imagemagick.org
  Copyright: Copyright (C) 1999-2011 ImageMagick Studio LLC
  Features: OpenMP  
````

### Kakadu
Install Kakadu [kdu_expand] [2]. We all wish this was easier and that there was 
an alternative. [Someday] [8]...

Make sure Kakadu shared object files are on your `LD_LIBRARY_PATH`.

Call `kdu_expand -v`

You should see something like this:

```
  This is Kakadu's "kdu_expand" application.
      Compiled against the Kakadu core system, version v6.0
      Current core system version is v6.0
```

These are also checked in the test suite.

Install Loris
-------------

These instructions assume you'll deploy as follows:

 * The `WSGI` script is at `/var/www/loris/loris.wsgi`
 * Other web files (for seadragon support) are at `/var/www/loris`
 * You'll be logging to `/var/log/loris`
 * You'll cache images at `/var/cache/loris`
 * The cron for cleaning the cache (if you want to use it) is in `/usr/local/bin`
 * If you choose to install manually, the rest of loris will be in 
   `/var/www/loris`, otherwise, it will be wherever `setup.py` puts it.

and that you're going to run the WSGI application in [_Daemon Mode_] [3].

Any of the above can be changed in `etc/loris.conf` and `etc/logging.conf`.

### To Begin...

 1. Clone loris to somewhere (like ~/loris): `git clone git@github.com:pulibrary/loris.git ~/loris`
 1. Make a user: `useradd -d /var/www/loris -s /sbin/false loris`
 1. Adjust/implement `loris.resolver` (see the file and _Resolving Identifiers_ below for details)
 1. Adjust `etc/loris.conf` (pay attention to the user/group and directories)
 1. Adjust `etc/logging.conf`
 1. Do one of the following (`setup.py` or 'Manual'):

#### Via `setup.py`

 1. Install [setuptools] [4] if necessary. 
    It's in apt and yum as `python-setuptools`.
 1. Run `python setup.py install` (probably w/ sudo or as root)
 1. Skip to _Update your Apache VirtualHost_ below.

#### Manual

Avoid this if possible; it's a drag.

 1. Install [Werkzeug] [5] 
 1. Install [Jinja2] [6]
 1. Make the directories: `mkdir /var/log/loris /var/cache/loris /etc/loris /var/www/loris /var/cache/loris`
 1. Copy the loris package to `/var/www/loris` (i.e. `cp -r ~/loris/loris /var/www/loris/loris`
 1. Copy the www files to `/var/www/loris` (i.e. `cp -r ~/loris/www/* /var/www/loris`)
 1. If you want to use the cache manager script: `cp -r ~/loris/bin/loris-cache_clean.sh /usr/local/bin`
 1. Copy the configuration files (i.e. cp `~/loris/etc/loris.conf` `~/loris/etc/logging.conf` `/etc/loris`)
 1. Adjust ownership: `chown -R loris:loris /var/log/loris /var/cache/loris /etc/loris /var/www/loris /var/cache/loris`
 1. Add the following to `/var/www/loris/loris.wsgi`:

```python
#!/usr/bin/env python
import sys                        # <----- this
sys.path.append('/var/www/loris') # <----- and this

from loris.app import create_app
application = create_app()
```

Configure Apache
----------------
```
AllowEncodedSlashes On # <--- Critical if you're using the default resolver!
WSGIDaemonProcess loris user=loris group=loris processes=10 threads=25 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi

<Directory /var/www/loris>
  WSGIProcessGroup loris
  WSGIApplicationGroup %{GLOBAL}
  Order allow,deny
  Allow from all
</Directory>
```
Restart.


Resolving Identifiers
---------------------
See `loris/resolver.py`. It depends what you're going to do here, but with the 
default you're going to at least need to change the `SRC_IMG_ROOT` constant. It 
is assumed that different users in different environment will likely need to 
implmenent the `resolve` function in `resolver.py` in different ways. 

`loris.resolver.resolve` must take a string that is an identifier as its only 
argument, and return a string that is absolute path on the local file system to 
a jp2.

That said... 

The supplied method for resolving identifiers to images is about as simple as 
it could be. In a request that looks like this 

    http://example.edu/loris/some/img/dir/0004/0,0,256,256/full/0/color.jpg

The portion between the path the to service on the host server and the region, 
(excluding leading and trailings `/`s), i.e.:

    http://example.edu/loris/some/img/dir/0004/0,0,256,256/full/0/color.jpg
                             \_______________/

will be joined to the `SRC_IMG_ROOT` constant, and have `.jp2` appended. So if

    SRC_IMG_ROOT=/usr/local/share/images

then this file must exist:

    /usr/local/share/images/some/img/dir/0004.jp2 

According to the IIIF specification, [the identifier must be URL encoded] [7], 
but with the supplied implementation either will work, i.e. `some/img/dir/0004` 
or `some%2Fimg%2Fdir%2F0004`. __Make sure `AllowEncodedSlashes` is set to `On` 
in your Apache configuration.__ 

Cache Management
----------------
See `bin/loris-cache_clean.sh`. This simple script can be configured and 
deployed as a cron job. See the script for details.
 1. Set LOG, CACHE_DIR, REDUCE_TO
 1. crontab -e -u loris ...

_TODO_ Embedded Mode
--------------------
Doc how to safely use 'Embedded Mode' see:
 * http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines#Defining_Process_Groups
 * http://code.google.com/p/modwsgi/wiki/ProcessesAndThreading

[1]: http://www.imagemagick.org/script/binary-releases.php "ImageMagick Binary Releases"
[2]: http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22 "Kakadu Installation"
[3]: http://code.google.com/p/modwsgi/#Modes_Of_Operation "WSGI Modes of Operation"
[4]: http://pypi.python.org/pypi/setuptools "Python setuptools"
[5]: http://werkzeug.pocoo.org/docs/installation/#installing-a-released-version "Werkzeug: Installing a released version"
[6]: http://jinja.pocoo.org/docs/intro/#installation "Jinja2 Installation"
[7]: http://www-sul.stanford.edu/iiif/image-api/#url_encoding "IIIF URL Encoding and Decoding"
[8]: http://www.openjpeg.org/ "OpenJPEG"
