Loris JPEG 2000 Server
========================

Loris is a lightweight implementation of the 
[International Image Interoperability Framework: Image API 1.0] [1]. More about 
this is discussed under IIIF 1.0 Compliance [link!] below.

Design
------
Loris is designed to stand on the shoulders of giants. Essentially, all it 
does is parse [IIIF URLs] [2] into a set of objects (in the source these are 
the `RegionParameter`, `SizeParameter`, and `RotationParameter` classes) that 
are then used to build utility command lines that are shelled out.

The [Werkzeug Python WSGI Utility Library] [3] handles the URL parsing and 
routing and supplies a few other conveniences.

Deployment
----------
# TODO

Tests
-----
Run `./tests.py`.

Source JPEG 2000 Images
-----------------------
# TODO - give PUL sample recipes.

Return Formats
--------------
Right now `jpg` and `png` are supported. The latter is underdeveloped and not 
terribly performant, but is in place so that all of the necessary branching in 
the content negotiation and rendering could be put in place and tested.

Resolving Identifiers
---------------------
The method for resolving identifiers to images is about as simple as it could 
be. In a request that looks like this 

  http://example.com/images/some/img/dir/0004/0,0,256,256/full/0/color.jpg

The portion between the path the to service on the host server and the region, 
i.e.:

  http://example.com/images/some/img/dir/0004/0,0,256,256/full/0/color.jpg
                           \________________/

will be joined to the `src_img_root` property, and have `.jp2` appended. So if

  [directories]
  ...
  src_img_root=/usr/local/share/images

then this file must exist:

  /usr/local/share/images/some/img/dir/0004.jp2 

This can be revised to fit other environments by replacing the 
`Loris#_resolve_identifier(self, ident)` method.

Dependencies
------------
Addition Python libraries:
 * [Werkzeug] [3] ([Installation] [5])

System Utilites
 * `kdu_expand`
 * `convert` (ImageMagick)


Both of the above should be on your PATH and executable from the command line.

Loris was developed on Ubuntu 12.04 with Python 2.7.2 and has only been tested
in that environment.

Logging
-------
Logging is set up in `loris.conf` and is extremely loud by default. Then 
handlers configured near the bottom of that file control the levels and 
directories. The directories must exist and be writable.

The Name
--------
Could stand for __Lightweight Open Repository Image Server__ or not. Thanks to
[shaune](https://github.com/sdellis, 'Shaun Ellis') for coming up with it.

IIIF 1.0 Compliance
-------------------
Loris aims to be [IIIF Level] [4] 1 compliant, with all of the Level 2 
Region, Size, and Rotation parameters and features supported. The easiest way 
to understand the request [URL syntax] [2] is to read the spec.

There are some configuration options that could break compliance, 
(specifically, see use_415 and use_201 in `loris.conf`)

<table>
  <tbody>
    <tr>
      <th></th>
      <td><span style="font-weight: bold;">Level 0</span></td>
      <th>Level 1</th>
      <th>Level 2</th>
      <th>Optional</th>
      <th><span style="color: red;">Loris</span></th>
    </tr>
    <tr>
      <td><strong>Region</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td><span style="color: red;"></span></td>
    </tr>
    <tr>
      <td>&nbsp; full</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;x,y,w,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;pct:x,y,w,h</td>
      <td></td>
      <td><br>
      </td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
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
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;w,</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;pct:x</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;!w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;!pct:x</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="font-style: italic;">Not mentioned in the spec</span></td>
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
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp; 90,180,270</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
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
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;color</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;grey</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp;&nbsp;bitonal</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
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
      <td><span style="color: red;">x</span></td>
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
      <td><span style="color: red;">x</span></td>
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
      <td><span style="font-weight: bold;">Image Information Request</span></td>
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
      <td><span style="color: red;">x</span></td>
    </tr>
    <tr>
      <td>&nbsp; xml response</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td><span style="color: red;">x</span></td>
    </tr>
  </tbody>
</table>

[1]: http://www-sul.stanford.edu/iiif/image-api/ "International Image Interoperability Framework: Image API 1.0"
[2]: http://www-sul.stanford.edu/iiif/image-api/#url_syntax "IIIF URL Syntax"
[3]: http://werkzeug.pocoo.org/ "Werkzeug Python WSGI Utility Library"
[4]: http://www-sul.stanford.edu/iiif/image-api/compliance.html "IIIF Levels"
[5]: http://werkzeug.pocoo.org/docs/installation/ "Werkzeug Installation"