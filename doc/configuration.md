Configuration and Options
=========================

See `etc/loris.conf` (or `/etc/loris/loris.conf` after you've run `setup.py install`).

In addition to a bunch of directory paths (items that end with `_dp`) which should be self-explanatory and the [transformation options explained below](#image-transformations), there are some options:

**Quick Start:** Nearly everything should fine with the default settings. As long as you're pointing to `kdu_expand` and the Kakadu libs (as discussed in the [previous](dependencies.md) section) and pointing to an sRGB icc color profile on your system in the `[transforms.jp2]` section (you can download a copy from the [International Color Consortium](http://www.color.org/srgbprofiles.xalter) or disable this feature by setting `map_embedded_profile_to_srgb=0`), you can proceed to [Cache Maintenance](cache_maintenance.md) and come back later.

### `[loris.Loris]`

 * `tmp_dp`. A temporary directory that loris can write to. `setup.py` will create this for you.

 * `www_dp`. The destination for the WSGI script. If you change this, it needs to be reflected in the Apache configuration (see [Apache Deployment Notes](apache.md)).

 * `run_as_user` and `run_as_group`. These are the user and group that will own the loris processes. When `setup.py` is run (likely as root or with sudo, everything is adusted to suit this owner.

 * `default_format`. Default format to return when no request format is supplied in the URI (`*.jpg`, `*.png`, etc.) or HTTP `Accept` header. Value is any three character value for a supported format from [Section 4.5](http://goo.gl/3BqIJ) of the spec. Out of the box, `jpg`,`png`, `tif`, and `gif` are supported.

 * `enable_caching`. If `enable_caching=0` no Memory or filesystem caching will happen and `Last-Modified` headers not be sent. This should only be used for testing/development/debugging.

 * `redirect_base_uri`. If `redirect_base_uri=1`, when a base URI is dereferenced (i.e. `{scheme}://{server}{/prefix}/{identifier}`) the server will redirect to `{scheme}://{server}{/prefix}/{identifier}/info.json` with a `303`. Otherwise the info json is just returned directly. 

 * `redirect_canonical_image_request` .If `redirect_canonical_image_request=1` and the request for an image is not the canonical path (e.g. only a width is supplied and the height is calculated by the server), the client will be redirected a `301`.

 * `redirect_conneg`. If `redirect_conneg=1` when asking for, e.g., `/info` with `Accept: application/json` (as opposed to the canonical `/info.json`), the client will be redirected with a `301` to `/info.json`. This also applies to image requests.

 * `enable_cors` / `cors_whitelist`. If `enable_cors=1`, the following property, `cors_whitelist` will be read and and the `Origin` header of the request will be checked against that list. If there is a match, the [`Access-Control-Allow-Origin`](http://www.w3.org/TR/cors/#access-control-allow-origin-response-header) will contain that value and the request should go through. **The value of this option can also be set to `*`**, which will make info requests publicly available (responses will include `Access-Control-Allow-Origin=*`)

 Note that you can also supply a `callback` parameter to requests (e.g. `?callback=myfunct`) to do [JSONP](http://en.wikipedia.org/wiki/JSONP) style requests. (This is not part of the IIIF API and may not work--probably will not--work with on other implementations.

### `[logging]`

Each module has its own logger and is chock-full of debug statements, so setting the level to to `INFO` or higher is highly recommended. 

The options are fairly self-explanatory; a few pointers
 
 * `log_to`. Can be `file` or `console` If set to `console`, and you're in production behind Apache, statements will go to Apache's logs. `DEBUG` and `INFO` are mapped to stdout, the rest to stderr.
 * `log_level`. Can be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`

 The rest only matter if `log_to=file`:

 * `log_dir`. This MUST exist and be writable. `setup.py` will take care of this,
 but it's your responsibility if you make changes once deployed.
 * `max_size`. Is in bytes, e.g. 5242880 == 5 MB
 * `max_backups`. This many previous logs will be kept.
 * `format`. Format of the log entries. See [Python LogRecord attributes](http://docs.python.org/2/library/logging.html#logrecord-attributes) for options.

### `[resolver.Resolver]`

Any options you add here will be passed through to the resolver you implement. For an explanation of the default resolver, see the [Resolver page](resolver.md).

### `[transforms.*]`

Probably safe to leave these as-is. See the [Developer Notes](develop.md#image-transformations) for when this may not be the case. The exceptions are `kdu_expand` and `kdu_libs` in the `[transforms.jp2]` (see [Installing Dependenccies](dependencies.md) step 2) or if you're not concerned about color profiles (see next).

### `[transforms.jp2]`
 * `map_embedded_profile_to_srgb`. If set to `map_embedded_profile_to_srgb=1` and you provide a path to an sRGB color profile on your system, e.g.:
``` 
...
map_embedded_profile_to_srgb=1
srgb_profile_fp=/usr/share/color/icc/colord/sRGB.icc
```

Then Loris will, as the name of the option suggests, map the color profile that is embedded in the JP2 to sRGB. To faciliate this, the Python Imaging Library has to be installed with [Little CMS](http://www.littlecms.com/) support. Instructions on how to do this are on the [Configuration page](configuration.md).

* * *

Proceed to [Cache Maintenance](cache_maintenance.md) or go [Back to README](../README.md)
