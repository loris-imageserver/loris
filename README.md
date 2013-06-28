![loris icon](https://github.com/pulibrary/loris/blob/master/www/icons/loris-icon-name.png?raw=true)  Loris IIIF Image Server
=======================

## Do Not!
Run `setup.py` until you've read this file. You have some work to do. In 
particular, you need to:
 * [Install dependencies](#dependencies)
 * [Set configuration options](#configuration)
 * [Run tests](#testing-and-developmentdebugging)
 * [Configure a resolver](#resolving-identifiers)
 * [Configure logging](#logging)
 * [Look at the tranformations and make sure the format you have/want are supported](#image-transformations)

## Dependencies
You need [Werkzeug](http://goo.gl/3IWJn) and 
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

## Configuration

In addition to a bunch of directory paths (items that end with `_dp`) which 
should be self-explanatory and the 
[transformation options explained below](#image-transformations), there are 
some options:

### Options
 * __Default Format__. 
 * __Enable Caching__. No Memory or filesystem caching will happen and 
   `Last-Modified` headers not be sent if `enable_caching=0`. 
 * __Redirect Base URIs.__ When a Base URI is dereferenced, should the image info be 
   returned, or should there be a `303` redirect? 
   Redirects if `redirect_base_uri=1`.
 * __Redirect Content Negotiation.__ When asking for, i.e., `/info` with 
   `Accept: application/json` (as opposed to the cannonical `/info.json`), 
   should the info request be fulfilled directly, or should the client be 
   redirected with a `301` to `/info.json`?  
   Redirects if `redirect_conneg=1`.
 * __Redirect Cannonical Image Request URI.__ If the request for an image is not 
   the cannonical path, should the application redirect with a 301? If this is 
   set to `0`, the URI for the cannonical image will be in `Link` header of the
   response. This is a non-normative feature.
   Redirects if `redirect_cannonical_image_request=1`.

### Notes Configuration for Developers

When developing or extending, note that the config file is turned into a 
dictionary of dictionaries at startup, e.g.:

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

__N.B.:__ When creating the application instance in debug mode (by calling 
`webapp.create_app(debug=True)`), __some properties in `etc/loris.conf` are 
overridden in the `create_app` function__. This is done so that we can 
calculate some locations based on the application directory.

Therefore, if you need to add additional properties, e.g. in your resolver or
transformations, you'll need to add them in two places: in `etc/loris.conf` and 
in the first `if` block in `webapp.create_app`.



## Testing and Development/Debugging
It is more than likely that you're going to need to add or tweak something, 
whether it's the resolver implementation or one of the image transformations, or 
something else. Even if that's not the case, with the image library dependencies
being so tricky, your going to want to run the tests to make sure everything is
in order.

Before you do that, you'll need to get all of the dependencies installed. Skip
down to _Installation Notes_ to do that, and then come back here.



## Running Tests
To run all of the tests, from the `/loris` directory (not `/loris/loris`) just 
run `./test.py`. If you just want to run the tests for a single module, do, e.g.
`python -m unittest -v tests.parameters_t` from the same dir as above, 



## Development/Debugging
`loris/webapp.py` is executable, and will start a [development server on port
5004](http://localhost:5004). From there you can work with the images that are 
included for testing by plugging any of these into the identifier slot:

 * `01%2F02%2F0001.jp2`
 * `01%2F03%2F0001.jpg`
 * `01%2F02%2Fgrey.jp2`
 * `01%2F04%2F0001.tif`

## Logging
Each module has its own logger and is chock-full of debug statements. Python 
logging is easier to configure with python code than with the config file 
syntax. See the comments in `loris/log_config.py` for details. You should be 
able to comment existing code in and out to get what you need. If you need to do
something radically different, have a look at the [Logging HOWTO](http://docs.python.org/2/howto/logging.html).

## Resolving Identifiers

The supplied implementation just unescapes the identifier tacks constant path 
onto the front. e.g. if `ident = 01%2F02%2F0001.jp2` and

```ini
[resolver.Resolver] 
src_img_root=/usr/local/share/images
```

then `Resolver.resolve(ident)` will return 

```
/usr/local/share/images/01/02/0001.jp2
```

You'll probably want to do something smarter. See `resolver._AbstractResolver` 
for details. Any properties you add in the `[resolver.Resolver]` section will 
automatically be in `self.config` as long as you subclass `_AbstractResolver`.

## Image Transformations

Loris is designed to make it possible for you to implement image 
transformations using using any libraries and utilities you choose. The 
transformers are loaded dynamically at startup, and are configured in 
`etc/loris.conf`. See `transforms.py` for details. Transformers for JPEG, TIFF, 
and JP2 (as long as you provide the Kakadu dependencies) using the PIL are 
supplied.

More about this. Every `_AbstractTransformer` implementation must implement a 
`transform()` method that receives a path to the source file (`src_fp`, the 
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
its confg dict.

At least for now, all implementation must be in (or aliased in) the 
transforms module.

IIIF 1.1 Compliance
-------------------
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
      <td>full</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>x,y,w,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>pct:x,y,w,h</td>
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
      <td>full</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>w,</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>,h</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>pct:x</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>!w,h</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
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
      <td> 0</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td> 90,180,270</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>arbitrary</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td>x</td>
    </tr>
    <tr>
      <td><strong>Quality</strong></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td> native</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>color</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>grey</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>bitonal</td>
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
      <td>jpeg</td>
      <td></td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>tif</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td>x</td>
    </tr>
    <tr>
      <td>png</td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
    <tr>
      <td>gif</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
      <td></td>
    </tr>
    <tr>
      <td>pdf</td>
      <td></td>
      <td></td>
      <td></td>
      <td>x</td>
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
      <td> json response</td>
      <td>x</td>
      <td>x</td>
      <td>x</td>
      <td></td>
      <td>x</td> 
    </tr>
  </tbody>
</table>





