Notes for Developers
====================

Configuration
-------------

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

which is then available in the `config` attribute of the application. The sub-dictionaries are then used to configure other objects, by passing the values of individual entries or just the entire dict, depending on how complex the situation is. Generally, the naming conventions and principals behind how this is intended to work should be clear.

__N.B.:__ When developing or extending, i.e., instantiating the application instance in debug mode (by calling `webapp.create_app(debug=True)`), __some properties in `etc/loris.conf` are overridden in the `create_app` function__. This is done so that we can calculate some locations based on the application directory. Therefore, if you need to add additional configuration, e.g. in your resolver or transformations, you may need to add/set them in two places if you want an option to be different when developing/running tests: in `etc/loris.conf` and in the first `if` block of `webapp.create_app`.

Running Tests
-------------
To run the tests, you need to install test dependencies:

```console
$ pip install -r requirements_test.txt
```

Then, in the root of the repository, run:

```console
$ coverage run -m py.test tests/*.py
$ coverage report
```

This will run the tests, and print coverage information for the ``loris`` directory.
If you'd like to run a specific test, pass a filename to ``coverage run``.
For example:

```console
$ coverage run -m py.test tests/parameters_t.py
```

Using the Development Server
----------------------------
`loris/webapp.py` is executable, and will start a development server at [localhost:5004](http://localhost:5004). From there you can work with the images that are included for testing by plugging any of these into the identifier slot:

 * `01%2F02%2F0001.jp2`
 * `01%2F03%2F0001.jpg`
 * `01%2F02%2Fgray.jp2`
 * `01%2F04%2F0001.tif`
 * `47102787.jp2` # use this one to make sure color profile mapping is working.

Image Transformations
---------------------
Loris is designed to make it possible for you to implement image transformations using any libraries or utilities you choose. The transformers are loaded dynamically at startup, and are configured in `etc/loris.conf`. See `transforms.py` for details. Transformers for JPEG, TIFF, GIF, and JP2 (JP2 as long as you provide the Kakadu dependencies) using Pillow are provided. 

More about this. Every `_AbstractTransformer` implementation must implement a `transform()` method that receives the path to the source file (`src_fp`), the path to where the output file should go (`target_fp`), and an instance of an `img.ImageRequest` object. This object should contain all of the attributes you could ever possbily need for working with an image library. See `img.ImageRequest.__slots__` for details.

`[transforms][[{fmt}]]` is the naming convention for of these sections in `etc/loris.conf`. This MUST be followed, and {fmy} MUST be one of the extension strings listed in the IIIF Image API specification.

Every section requires an `impl` key, and any other options provided will be automatically be available to the impl in its config dictionary.

At least for now, all implementation must be in (or aliased in) the transforms module. 

[Back to README](../README.md)

