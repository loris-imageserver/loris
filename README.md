![loris icon](https://github.com/pulibrary/loris/blob/master/www/icons/loris-icon-name.png?raw=true)  Loris JPEG 2000 Server
========================

Loris is an implementation of the 
[International Image Interoperability Framework: Image API 1.0] [1]. More about 
this is discussed under IIIF 1.0 Compliance below.

Dependencies
------------
Addition Python libraries:
 * [Werkzeug] [3] ([Installation] [5])
 * [Jinja] [6] ([Installation] [7])

System Utilites:
 * `kdu_expand`
 * ImageMagick (`convert`)

Both of the above should be on your PATH and executable from the command line. 

More on this in [deployment.md][8]

If your dependencies are in order, you should be able to start the dev server 
by executing `loris/app.py`, and this should work: 

http://localhost:5000/another/arbitrary/path/0004/1275,100,250,120/full/0/native.jpg

To get much further you're going to want to look at `resolver.py` (again, see 
[deployment.md][8]), but this should let you know that you're dependencies are
squared away.

Deployment
----------
See [deployment.md][8]

Loris was developed on Ubuntu 12.04 with Python 2.7, and deployed using Apache 
2.2.22. It has only been tested in that environment at this point.

Tests
-----
From the directory the top (`loris`) directory, call 

	python -m unittest -v test.suite

The tests should run in a logical order, so if you see a failure, futher 
failures might casacade and mask the problem. To solve this, you can have 
unittest stop at the first fail:

	python -m unittest -vf tests

You may want to turn down logging at first, and only turn it up if something 
goes wrong. __Note__ also that `Test_I_ResultantImg` takes a while 
(60 seconds?).

Return Formats
--------------
Right now `jpg` and `png` are supported. The latter is underdeveloped and not 
terribly performant, but is in place so that all of the necessary branching in 
the content negotiation and rendering could be put in place and tested.

Logging
-------
Logging is set up in `etc/logging.conf` The handlers configured near the bottom 
of that file control the levels and directories. The directories must exist and 
be writable.

The Name
--------
Could stand for __Lightweight Open Repository Image Server__ or not; It's a 
Lightweight image serve anyway. Thanks to 
[shaune](https://github.com/sdellis "Shaun Ellis") for coming up with it and 
creating the icons.

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
[6]: http://jinja.pocoo.org/ "Jinja2"
[7]: http://jinja.pocoo.org/docs/intro/#installation "Jinja2 Installation"
[8]: https://github.com/pulibrary/loris/blob/master/doc/deployment.md "Loris Deployment"