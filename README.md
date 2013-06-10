## Do Not!
Run `setup.py` until you've read this file.

## Configuration
See `etc/loris.conf`. This is a standard ini file, and is turned into a 
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

### Running Tests
To run all of the tests, from the `/loris` directory (not `/loris/loris`) just 
run `./test.py`. If you just want to run the tests for a single module, do, e.g.
`python -m unittest -v tests.parameters_t` from the same dir as above, 

### Development/Debugging
`loris/webapp.py` is execuatble, and will start a [development server on port
5000](http://localhost:5000). From there you can work with the images are are 
included for testing by plugging any of these in the identifier slot:

 * `01%2F02%2F0001.jp2`
 * `01%2F03%2F0001.jpg`
 * `01%2F02%2Fgrey.jp2`
 * `01%2F04%2F0001.tif`

## Logging
Python logging is easier to configure with python code than with the config file
syntax. See the comments in `loris/log_config.py` for details. You should be 
able to comment existing code in and out to get what you need.

## Resolving Identifiers

## Image Transformations

(talk about Parameter objects and expected public function signatures.)

## Configurable Options

### Redirects
 * __Base URIs.__ When a Base URI is dereferenced, should the image info be 
   returned, or should there be a `303` redirect? 
   Redirects if `redirect_base_uri=1`.
 * __Content Negotiation.__ When asking for, i.e., `/info` with 
   `Accept: application/json` (as opposed to the cannonical `/info.json`), 
   should the info request be fulfilled directly, or should the client be 
   redirected with a `301` to `/info.json`?  
   Redirects if `redirect_conneg=1`.
 * __Cannonical Image Request URI.__ If the request for an image is not the 
 	cannonical path, should the application redirect with a 301? If this is 
 	set to `0`, the URI for the cannonical image will be in `Link` header of the
 	response. This is a non-normative feature.
 	Redirects if `redirect_cannonical_image_request=1`.



## Installation Notes
You'll need to install some dependencies that can't be installed by pip.

### Ubuntu
It may be as simple as this:

```
sudo apt-get install python-imaging
sudo pip install werkzeug
```
But if you see:

```
...
*** JPEG support not available
...
```
or jpeg tests aren't passing, then have a look [here](http://codeinthehole.com/writing/how-to-install-pil-on-64-bit-ubuntu-1204/), or [here](http://obroll.com/install-python-pil-python-image-library-on-ubuntu-11-10-oneiric/).
