# ![loris icon](www/icons/loris-icon-name.png?raw=true)  Loris IIIF Image Server

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
 * [Python Imaging Library](http://goo.gl/E2Xv4)

For JPEG2000 support you also need [Kakadu](http://goo.gl/owJN8), and the 
`kdu_expand` command line application in particular. Set the path to the libs
and the executable in the [configuration file](#configuration).

PIL can be cause problems in particular because of its `libjpeg` and `zlib` 
dependencies. You're best off getting it from a package manager, but even after
that you may have trouble. Have a Google for 
[posts like this](http://goo.gl/Jv9J0) about getting it working on your system. 

## Configuration and Options

In addition to a bunch of directory paths (items that end with `_dp`) which 
should be self-explanatory and the 
[transformation options explained below](#image-transformations), there are 
some options:
 * `run_as_user` and `run_as_group`. These are the user and group that will 
   own the loris processes. When `setup.py` is run, everything is adusted to suit
   this owner.
 * __Default Format__. Default format to return when no request format is 
   supplied in the URI (`*.jpg`, `*.png`, etc.) or HTTP `Accept` header. Value 
   is any three character value for a supported format from 
   [Section 4.5](http://goo.gl/3BqIJ) of the spec. Out of the box, `jpg`,`png`, 
   or `tif` are supported.
 * __Enable Caching__. No Memory or filesystem caching will happen and 
   `Last-Modified` headers not be sent if `enable_caching=0`. 
 * __Redirect Base URIs.__ When a Base URI is dereferenced, should the image 
   info be returned, or should there be a `303` redirect? 
   __Redirects if `redirect_base_uri=1`.__
 * __Redirect Content Negotiation.__ When asking for, i.e., `/info` with 
   `Accept: application/json` (as opposed to the cannonical `/info.json`), 
   should the info request be fulfilled directly, or should the client be 
   redirected with a `301` to `/info.json`?  
   Redirects if `redirect_conneg=1`.
 * __Redirect Cannonical Image Request URI.__ If the request for an image is not 
   the cannonical path, should the application redirect with a `301`?
   __Redirects if `redirect_cannonical_image_request=1`.__

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
Each module has its own logger and is chock-full of debug statements. IMO, 
Python logging is easier to configure with python code than with the config 
file syntax. See the comments in `loris/log_config.py` for details. You should 
be able to comment existing code in and out to get what you need. If you need 
to do something radically different, have a look at the  
[Python Logging HOWTO](http://docs.python.org/2/howto/logging.html).

There is also a sample file in the loris package called 
`log_config.py.production_sample` that can be used for reference.

## Resolving Identifiers
The supplied implementation just unescapes the identifier and tacks constant 
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
`transforms.py` for details. Transformers for JPEG, TIFF, and JP2 (JP2 as 
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

At least for now, all implementation must be in (or aliased in) the 
transforms module.

## Caching
There is a Bash script at [`bin/loris-cache_clean.sh`](bin/loris-cache_clean.sh) 
that makes heavy use of `find` command line utility to turn the filesystem 
cache into a simple LRU-style cache. Have a look at it; it is intended to be 
deployed as a cron job.

## Apache Configuration

How to deploy a WSGI web application is out of scope for this document, but this
should help you get started:

```
AllowEncodedSlashes On # Critical if you're using the default resolver!
WSGIDaemonProcess loris user=loris group=loris processes=5 threads=5 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi
WSGIProcessGroup loris
```

On RedHat only you'll likely need to add
```
WSGISocketPrefix /var/run/wsgi
```
as well. See: [Location of Unix Sockets](http://code.google.com/p/modwsgi/wiki/ConfigurationIssues#Location_Of_UNIX_Sockets)

## IIIF 1.1 Compliance
See [doc/compliance.md](doc/compliance.md)
