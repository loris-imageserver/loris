# ![loris icon](www/icons/loris-icon-name.png?raw=true)  Loris IIIF Image Server

## Demos
 * [Mentelin Bible, l. 1r](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/native.jpg)
 * [Serving Images for OpenSeadragon](http://libimages.princeton.edu/osd-demo)

## Do Not!
Run `setup.py` until you've read this file. You have some work to do. In 
particular, you need to:

 * [Install dependencies](#dependencies)
 * [Set configuration options](#configuration)
 * [Run tests](#testing-and-developmentdebugging)
 * [Configure a resolver](#resolving-identifiers)
 * [Configure logging](#logging)
 * [Look at the tranformations and make sure the format you have/want are supported](#image-transformations)

After all that you can run `python ./setup.py install` and it will put 
everything in the correct places and set permissions.

## Dependencies
You need [Werkzeug](http://goo.gl/3IWJn) (`>=0.8.3`) and 
[PIL](http://goo.gl/E2Xv4). `setup.py` will install Werkzeug
but:

 1. You should run tests before installing
 2. The Python Imaging Library has dependencies that you can't get with 
 `easy_install` or `pip`.

So you're better off installing these manually:

 * [Werkzeug](http://goo.gl/sPiHo)
 * [Python Imaging Library](http://goo.gl/E2Xv4). See [further down the page](#installing-pil) for 
 more specific instructions.

For JPEG2000 support you also need [Kakadu](http://goo.gl/owJN8), and the 
`kdu_expand` command line application in particular. Set the path to the libs
and the executable in the [configuration file](#configuration).

PIL can be cause problems in particular because of its `libjpeg` and `zlib` 
dependencies. See [further down the page](#installing-pil) or have a Google for [posts like this](http://goo.gl/Jv9J0) about getting 
it working on your system. 

## Configuration and Options

See `etc/loris.conf` (or `/etc/loris/loris.conf` after you've run `setup.py install`).

In addition to a bunch of directory paths (items that end with `_dp`) which 
should be self-explanatory and the 
[transformation options explained below](#image-transformations), there are 
some options:

 * `run_as_user` and `run_as_group`. These are the user and group that will 
   own the loris processes. When `setup.py` is run (likely as root or with sudo, 
   everything is adusted to suit this owner.

 * __Default Format__. Default format to return when no request format is 
   supplied in the URI (`*.jpg`, `*.png`, etc.) or HTTP `Accept` header. Value 
   is any three character value for a supported format from 
   [Section 4.5](http://goo.gl/3BqIJ) of the spec. Out of the box, `jpg`,`png`, 
   `tif`, and `gif` are supported.

 * __Enable Caching__. If `enable_caching=0` no Memory or filesystem caching 
   will happen and `Last-Modified` headers not be sent. This should only be used
   for testing/debugging.

 * __Redirect Base URIs.__ If `1`, when a base URI is dereferenced (i.e. 
   `{scheme}://{server}{/prefix}/{identifier}`) the server will redirect to
   `{scheme}://{server}{/prefix}/{identifier}/**info.json**` with a `303`. Otherwise
   the info json is just returned. 

 * __Redirect Content Negotiation.__ If `1` when asking for, e.g., `/info` with 
   `Accept: application/json` (as opposed to the cannonical `/info.json`), 
   the client will be redirected with a `301` to `/info.json`. This also applies
   to image requests.

 * __Redirect Cannonical Image Request URI.__ If `1` and the request for an 
   image is not the cannonical path (e.g. only a width is supplied and the 
   height is calculated by the server, the client will be redirected a `301`.

 * __Enable CORS / CORS Whitelist.__ If `enable_cors` is set to `1`, the 
  following property, `cors_whitelist` will be read and and the `Origin` header 
  of the request will be checked against that list. If there is a match, the 
  [`Access-Control-Allow-Origin`](http://www.w3.org/TR/cors/#access-control-allow-origin-response-header) will contain that value and the request 
  should go through.

  Note that you can also supply a `callback` parameter to requests (e.g. 
  `?callback=myfunct`) to do [JSONP](http://en.wikipedia.org/wiki/JSONP) style 
  requests. (This is not part of the IIIF API and may not work--probably will 
  not--work with onther implementations.

There is one other option worth noting, under the `transforms.jp2` section. If:

 1. `map_embedded_profile_to_srgb` is set to `1` 
 2. You provide a path to an sRGB color profile on your system, and
 3. You're using Kakadu 7.2 or later

e.g.:

```
[transforms.jp2]
...
map_embedded_profile_to_srgb=1
srgb_profile_fp=/usr/share/color/icc/colord/sRGB.icc
```

Then Loris will, as the name of the option suggests, map the color profile that 
is embedded in the JP2 to sRGB. To faciliate this, the Python Imaging Library has
to be BUILT with [Little CMS](http://www.littlecms.com/) support. Instructions on
how to do this (at least on an Ubuntu system) are [further down the page](#installing-pil).

### Notes about Configuration for Developers

The config file is turned into a dictionary of dictionaries at startup, e.g.:

```ini
[loris.Loris]
cache_dp=/tmp/loris/cache
tmp_dp=/tmp/loris
...
[resolver.Resolver]
src_img_root=/usr/local/share/images
```

yields

```python
config = {
	'loris.Loris': {
		'cache_dp' : '/tmp/loris/cache',
		'tmp_dp' : '/tmp/loris'
	},

	'resolver.Resolver' {
		'src_img_root' : '/usr/local/share/images'
	}
}
```

which is then available in the `config` attribute of the application. The 
sub-dictionaries are then be used to configure other objects, either by passing
the values of individual entries or just the entire dict, depending on how 
complex the situation is. Generally, the naming conventions and principals 
behind how this is intended to work should be clear.

__N.B.:__ When developing or extending, i.e., instantiating the application 
instance in debug mode (by calling `webapp.create_app(debug=True)`), __some 
properties in `etc/loris.conf` are overridden in the `create_app` function__. 
This is done so that we can calculate some locations based on the application 
directory.

Therefore, if you need to add additional properties, e.g. in your resolver or
transformations, you may need to add them in two places: in `etc/loris.conf` and 
in the first `if` block of `webapp.create_app`.

## Testing and Development/Debugging
It is more than likely that you're going to need to add or tweak something, 
whether it's the resolver implementation or one of the image transformations, or 
something else. Even if that's not the case, with the image library dependencies
being so tricky, your going to want to run the tests to make sure everything is
in order.

Before you do that, you'll need to get all of the [dependencies](#dependencies) 
installed.

### Running Tests
To run all of the tests, from the `/loris` directory (not `/loris/loris`) just 
run `./test.py`. If you just want to run the tests for a single module, do, e.g.
`python -m unittest -v tests.parameters_t` from the same dir as above, 

### Development/Debugging
`loris/webapp.py` is executable, and will start a [development server on port
5004](http://localhost:5004). From there you can work with the images that are 
included for testing by plugging any of these into the identifier slot:

 * `01%2F02%2F0001.jp2`
 * `01%2F03%2F0001.jpg`
 * `01%2F02%2Fgrey.jp2`
 * `01%2F04%2F0001.tif`

## Logging

**If a configuration file is found is `/etc/loris/loris.conf` then it will be 
read, even if you are running the development server in debug mode.**

Each module has its own logger and is chock-full of debug statements, so setting
the level to to `INFO` or higher is highly recommended. Logging is configured
in `loris.conf` in the `log` section:

```ini
log_to=file ; [console|file]
log_level=WARNING ; [DEBUG|INFO|WARNING|ERROR|CRITICAL]
log_dir=/var/log/loris
max_size=5242880
max_backups=5
```

The options are fairly self-explanatory; a few pointers
 
 * `log_to`. Can be `file` or `console` If set to `console`, and you're in production behind Apache, statements will go to Apache's logs. `DEBUG` and `INFO` are mapped to stdout, the rest to stderr.
 * `log_level`. Can be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`

 The rest only matter if `log_to` is set to `file`.

 * `log_dir`. This MUST exist and be writable. `setup.py` will take care of this,
 but it's your responsibility if you make changes once deployed.
 * `max_size`. Is in bytes, e.g. 5242880 == 5 MB
 * `max_backups`. This many previous logs will be kept.




## Resolving Identifiers
The supplied implementation just unescapes the identifier and tacks a constant 
path onto the front. e.g. if `ident = 01%2F02%2F0001.jp2` and in the config 
file:

```ini
[resolver.Resolver] 
src_img_root=/usr/local/share/images
```

then `app.resolver.resolve(ident)` will return 

```
/usr/local/share/images/01/02/0001.jp2
```

You'll probably want to do something smarter. See `resolver._AbstractResolver` 
for details. Note that any properties you add in the `[resolver.Resolver]` 
section will be in the `self.config` dictionary as long as you subclass
`_AbstractResolver`.

## Image Transformations
Loris is designed to make it possible for you to implement image 
transformations using any libraries and utilities you choose. The transformers 
are loaded dynamically at startup, and are configured in `etc/loris.conf`. See 
`transforms.py` for details. Transformers for JPEG, TIFF, GIF, and JP2 (JP2 as 
long as you provide the Kakadu dependencies) using the Python Imaging Library 
are provided. 

More about this. Every `_AbstractTransformer` implementation must implement a 
`transform()` method that receives the path to the source file (`src_fp`), the 
path to where the output file should go (`target_fp`), and an instance of an 
`img.ImageRequest` object. This object should contain all of the attributes you 
could ever possbily need for working with an image library. See
`img.ImageRequest.__slots__` for details.

`transforms.{src_format}` is the naming convention for of these sections in 
`etc/loris.conf`. This MUST be followed, and {src_format} MUST be one of the 
[extension strings listed in section 4.5](http://www-sul.stanford.edu/iiif/image-api/1.1/#format).

Every section requires these options:

 * src_format
 * impl
 * target_formats

any other options provided will be automatically be available to the impl in 
its config dictionary.

At least for now, all implementation must be in (or aliased in) the transforms 
module.

## Caching
There is a Bash script at [`bin/loris-cache_clean.sh`](bin/loris-cache_clean.sh) 
that makes heavy use of `find` command line utility to turn the filesystem 
cache into a simple LRU-style cache. Have a look at it; it is intended to be 
deployed as a cron job.

## Apache Configuration

How to deploy a WSGI web application is out of scope for this document, but this
should help you get started:

```
AllowEncodedSlashes On 
WSGIDaemonProcess loris user=loris group=loris processes=3 threads=15 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi
WSGIProcessGroup loris
```

Also, Loris is setting `Last-Modified` headers, but not `Cache-Control` or 
`Expires`. To do that, add:

```
ExpiresActive On
ExpiresDefault "access plus 5184000 seconds"
```

You'll need the `expires` and `headers` modules enabled.

On RedHat only you'll likely need to add
```
WSGISocketPrefix /var/run/wsgi
```
as well. See: [Location of Unix Sockets](http://code.google.com/p/modwsgi/wiki/ConfigurationIssues#Location_Of_UNIX_Sockets)

## Installing PIL

These instructions are known to work with Ubuntu 12.04.3. If you have further
information, please provide it!

First, remove all instances of PIL, including, but not limited to, the `python-imaging` package:

```
sudo pip uninstall PIL
sudo apt-get purge python-imaging
```

Then, get install all of the dependencies:

```
sudo apt-get install libjpeg-turbo8 libjpeg-turbo8-dev libfreetype6 \
libfreetype6-dev zlib1g-dev liblcms liblcms-dev liblcms-utils
```

Link them the dirs where PIL will find them (this is unfortunate):

```
sudo ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
sudo ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/
sudo ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/
sudo ln -s /usr/lib/`uname -i`-linux-gnu/liblcms.so /usr/lib/ # check this
```

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

The Output MUST include these lines:

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

## IIIF 1.1 Compliance
See [doc/compliance.md](doc/compliance.md)

## License

Copyright (C) 2013 Jon Stroop

This program is free software: you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the Free 
Software Foundation, either version 3 of the License, or (at your option) 
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT 
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for 
more details.

You should have received a copy of the GNU General Public License along 
with this program. If not, see <http://www.gnu.org/licenses/>.
