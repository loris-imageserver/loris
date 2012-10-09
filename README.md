![loris icon](https://github.com/pulibrary/loris/blob/master/icons/loris-icon-name.png?raw=true)  Loris JPEG 2000 Server
========================

Loris is an implementation of the 
[International Image Interoperability Framework: Image API 1.0] [1]. More about 
this is discussed under IIIF 1.0 Compliance below.

Tests
-----
From the directory that contains `tests.py`, call 

	python -m unittest -v tests

The tests should run in a logical order, so if you see a failure, futher 
failures might casacade and mask the problem. To solve this, you can have 
unittest stop at the first fail:

	python -m unittest -vf tests

You may want to turn down logging at first, and only turn it up if something 
goes wrong. __Note__ that `Test_I_ResultantImg` takes a while.


Deployment
----------

__Note:__ All commands given are for deploying on Ubuntu. Your mileage may vary.
### Check it out:

	git clone https://github.com/pulibrary/loris.git loris

### Install and Test Dependencies:
__Install and test ImageMagick (convert)__ 


	sudo apt-get install imagemagick
	...
	convert -version

You should see something like this:

	Version: ImageMagick 6.6.9-7 2012-08-17 Q16 http://www.imagemagick.org
	Copyright: Copyright (C) 1999-2011 ImageMagick Studio LLC
	Features: OpenMP  

__Install Kakadu (kdu_expand)__  
Compile or download by following [the instructions on their site] [6]  

Make sure Kakadu shared object files are on your `LD_LIBRARY_PATH`.

### Configure for Apache

Make a WSGI file called `loris.wsgi` so the web server and loris can talk to 
each other.  Here is a sample WSGI file:

__loris.wsgi__

```python
#!/usr/bin/env python
import sys; 
sys.path.append('/path/to/loris')

from loris import create_app
application = create_app()
```

Here is a sample Apache virtual host file configuration (variables in { }):

```
...
AllowEncodedSlashes On # <--- Critical if you're using the default resolver!
WSGIScriptAlias {/loris} {/path/to/loris/loris.wsgi}
<Directory {/path/to/loris}>
	Order allow,deny
	Allow from all
</Directory>
...
```

Or, in 'Daemon Mode':

```
WSGIDaemonProcess loris user={user} group={group} threads=25 maximum-requests=10000
WSGIScriptAlias {/loris} {/path/to/loris/loris.wsgi}

<Directory {/path/to/loris}>
  WSGIProcessGroup loris
  WSGIApplicationGroup %{GLOBAL}
  Order allow,deny
  Allow from all
</Directory>
```

Note that both of these are likely over-simplified and WSGI [will require more tuning] [10]

Modify these lines (at least) in the `loris.conf` file:

	cache_root = /path/to/loris/dev_cache
	src_img_root = /path/to/loris/test_img

Restart Apache.  
Point your browser here to make sure it works with the test image:
http://your_server/loris/pudl0001/4609321/s42/00000004/info.xml

To see the full JP2 image as a jpg:
http://your_server/loris/pudl0001/4609321/s42/00000004/full/full/0/color.jpg

[More on URL syntax][2] is available via the spec.


Resolving Identifiers
---------------------
It is up to you to implmenent the `resolve` function in `resolver.py`. See the 
file for details. 

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

According the the specification, [the identifier must be URL encoded] [9], but 
with the supplied implementation either will work, i.e. `some/img/dir/0004` or
`some%2Fimg%2Fdir%2F0004`. __Make sure `AllowEncodedSlashes` is set to `On` in
your Apache configuration.__ 


Aside: _Identifier escaping/encoding of slashes should never really be necessary._ Consider the Request Syntax:

	http://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}

Any implementation should know its host and name, e.g.:

	http://{server}{/prefix}/

and the after `{identifier}` remainder of the syntax has only two patterns:

	/{region}/{size}/{rotation}/{quality}.{format}

or with conneg:

	/{region}/{size}/{rotation}/{quality}

so what could be in between those two portions of the URI __but__ the identifer?


Return Formats
--------------
Right now `jpg` and `png` are supported. The latter is underdeveloped and not 
terribly performant, but is in place so that all of the necessary branching in 
the content negotiation and rendering could be put in place and tested.

Dependencies
------------
Addition Python libraries:
 * [Werkzeug] [3] ([Installation] [5])
 * [Jinja] [7] ([Installation] [8])

System Utilites
 * `kdu_expand`
 * `convert` (ImageMagick)

Both of the above should be on your PATH and executable from the command line. 

Loris was developed on Ubuntu 12.04 with Python 2.7.2 and has only been tested
in that environment.

Configuration
-------------
Please read through `loris.conf`. Properties and options are explained there.

Logging
-------
Logging is set up in `loris.conf` and is extremely loud by default. The 
handlers configured near the bottom of that file control the levels and 
directories. The directories must exist and be writable.

Design
------
Loris is designed to stand on the shoulders of giants. Essentially, all it 
does is parse [IIIF URLs] [2] into a set of objects (in the source these are 
the `RegionParameter`, `SizeParameter`, and `RotationParameter` classes) that 
are then used to build utility command lines that are shelled out.

The [Werkzeug Python WSGI Utility Library] [3] handles the URL parsing and 
routing and supplies a few other convenience methods.

The Name
--------
Could stand for __Lightweight Open Repository Image Server__ or not. Thanks to
[shaune](https://github.com/sdellis "Shaun Ellis") for coming up with it and 
the icon.

IIIF 1.0 Compliance
-------------------
Loris aims to be [IIIF Level] [4] 1 compliant, with all of the Level 2 
Region, Size, and Rotation parameters and features supported. The easiest way 
to understand the request [URI syntax] [2] is to read the spec.

<table>
  <tbody>
    <tr>
      <th></th>
      <td><span style="font-weight: bold;">Level 0</td> 
      <th>Level 1</th>
      <th>Level 2</th>
      <th>Optional</th>
      <th>Loris</span></th>
    </tr>
    <tr>
      <td><strong>Region</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td> 
    </tr>
    <tr>
      <td>&nbsp; full</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;x,y,w,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;pct:x,y,w,h</td>
      <td></td>
      <td><br>
      </td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td><strong>Size</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp; full</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;w,</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;pct:x</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;!w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;!pct:x</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="font-style: italic;">Not mentioned in the spec</td> 
    </tr>
    <tr>
      <td><strong>Rotation</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp; 0</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp; 90,180,270</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;arbitrary</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
    </tr>
    <tr>
      <td><strong>Quality</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp; native</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;color</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;grey</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;bitonal</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td><strong>Format</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;jpeg</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;tif</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;png</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp;&nbsp;gif</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;pdf</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;jp2</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td><strong>Image Information Request</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>&nbsp; json response</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>&nbsp; xml response</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
  </tbody>
</table>

[1]: http://www-sul.stanford.edu/iiif/image-api/ "International Image Interoperability Framework: Image API 1.0"
[2]: http://www-sul.stanford.edu/iiif/image-api/#url_syntax "IIIF URL Syntax"
[3]: http://werkzeug.pocoo.org/ "Werkzeug Python WSGI Utility Library"
[4]: http://www-sul.stanford.edu/iiif/image-api/compliance.html "IIIF Levels"
[5]: http://werkzeug.pocoo.org/docs/installation/ "Werkzeug Installation"
[6]: http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22 "Kakadu Installation"
[7]: http://jinja.pocoo.org/ "Jinja2"
[8]: http://jinja.pocoo.org/docs/intro/#installation "Jinja2 Installation"
[9]: http://www-sul.stanford.edu/iiif/image-api/#url_encoding "IIIF URL Encoding and Decoding"
[10]: http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines "WSGI Configuration Guidelines"