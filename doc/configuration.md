Configuration and Options
=========================

See `etc/loris2.conf`.

In addition to a bunch of directory paths (items that end with `_dp`) which should be self-explanatory and the [transformation options explained below](#image-transformations), there are some options:

**Quick Start:** Nearly everything should fine with the default settings. As long as you're pointing to `kdu_expand` and the Kakadu libs (as discussed in the [previous](dependencies.md) section) you can proceed to [Cache Maintenance](cache_maintenance.md) and come back later.

Environment variables are loaded into the `[DEFAULT]` section of the config file in memory, and `Template`-style [string interpolation] is on. This means you can pull in config information from the environment instead of hardcoding it in the config file. For example:

```
...
# get user and group from the environment
run_as_user='$USER'
run_as_group='$GROUP'
...
```


### `[loris.Loris]`

 * `tmp_dp`. A temporary directory that loris can write to. `setup.py` will create this for you.
 * `www_dp`. The destination for the WSGI script. If you change this, it needs to be reflected in the Apache configuration (see [Apache Deployment Notes](apache.md)).
 * `run_as_user` and `run_as_group`. These are the user and group that own the loris processes.
 * `enable_caching`. If `enable_caching=False` no Memory or filesystem caching will happen and `Last-Modified` headers not be sent. This should really only be used for testing/development/debugging.
 * `redirect_canonical_image_request`. If `redirect_canonical_image_request=True` and the request for an image is not the canonical path (e.g. only a width is supplied and the height is calculated by the server), the client will be redirected a `301`.
 * `redirect_id_slash_to_info` If True, `{id}/` and `{id}` will both redirect to the `{id}/info.json`. This is generally OK unless you have ids that end in slashes.
 * `max_size_above_full` A numerical value which restricts the maximum image size to `max_size_above_full` percent of
    the original image size. Setting this value to 100 disables server side interpolation of images. Default value is 200 (maximum double width or height allowed). To allow any size, set this value to 0.
 * `proxy_path` The path you would like loris to proxy to. This will override the default path to your info.json file. proxy_path defaults to None if not explicitly set.

### `[logging]`

Each module has its own logger and is chock-full of debug statements, so setting the level to to `INFO` or higher is highly recommended.

The options are fairly self-explanatory; a few pointers

 * `log_to`. Can be `file` or `console` If set to `console`, and you're in production behind Apache, statements will go to Apache's logs. `DEBUG` and `INFO` are mapped to stdout, the rest to stderr.
 * `log_level`. Can be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`
 * `format`. Format of the log entries. See [Python LogRecord attributes](http://docs.python.org/2/library/logging.html#logrecord-attributes) for options.

 The rest only matter if `log_to=file`:

 * `log_dir`. This MUST exist and be writable. `setup.py` will take care of this, but it's your responsibility if you make changes once deployed.
 * `max_size`. Is in bytes, e.g. 5242880 == 5 MB
 * `max_backups`. This many previous logs will be kept.

### `[resolver]`

Any options you add here will be passed through to the resolver you implement. For an explanation of some of the resolvers, see the [Resolver page](resolver.md).

### `[transforms]`

Probably safe to leave these as-is unless you care about something very specific. See the [Developer Notes](develop.md#image-transformations) for when this may not be the case. The exceptions are `kdu_expand` and `kdu_libs` in the `[transforms.jp2]` (see [Installing Dependencies](dependencies.md) step 2) or if you're not concerned about color profiles (see next).

### `[transforms][[jp2]]`
 * `map_profile_to_srgb`. If set to `map_profile_to_srgb = True` and you provide a path to an sRGB color profile on your system, e.g.:
```
...
map_profile_to_srgb=True
srgb_profile_fp=/usr/share/color/icc/colord/sRGB.icc
```

Then Loris will, as the name of the option suggests, map the color profile that is embedded in the JP2 to sRGB. To facilitate this, the Python Imaging Library has to be installed with [Little CMS](http://www.littlecms.com/) support. Instructions on how to do this are on the [Configuration page](configuration.md).

* * *

Proceed to [Cache Maintenance](cache_maintenance.md) or go [Back to README](../README.md)

[string interpolation]: http://www.voidspace.org.uk/python/configobj.html#string-interpolation
