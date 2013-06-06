## Do Not!
...run `setup.py` until you've read this file.

## Configuration
See `etc/loris.conf`. This is a standard ini file, and is turned into a 
dictionary of dictionaries e.g.:

```ini
[loris.Loris]
cache_dp=/tmp/loris/cache
tmp_dp=/tmp/loris
...
[resolver.Resolver]
src_img_root=/usr/local/share/images
```

yield

which is then available in the `config` attribute of the application. The 
sub-dictionaries are then be used to configure other objects, either by passing
the values of individual entries or just the entire dict, depending on how 
complex the situation is. Generally, the naming conventions and principals 
behind how this is intended to work should be clear. 

__N.B.:__ When creating the application instance in debug mode (by calling 
`webapp.create_app(debug=True)`), __some properties `etc/loris.conf` are 
overridden in the `create_app` function__. This is done so that we can 
calculate some locations based on the application directory.

Therefore, if you need to add additional properties, e.g. in your resolver or
transformations, you'll need to add them in two places: in `etc/loris.conf` and 
in the first `if` block in `webapp.create_app`.

## Testing and Debugging.
It is more than likely that you're going to need to add or tweak something, 
whether it's the resolver implementation or one of the image transformations, or 
something else. Even if that's not the case, with the image library dependencies
being so tricky, your going to want to run the test.


## Installation Notes
You'll need to install some dependencies that can't be installed by pip.

### Ubuntu
```
sudo apt-get install libjpeg-turbo-progs

sudo apt-get install python-imaging 
```
May need to make symlinks for python imaging.

pip install werkzeug