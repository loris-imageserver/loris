Resolving Identifiers
=====================

### `SimpleFSResolver`

This supplied implementation just unescapes the identifier and tacks a constant path onto the front. e.g. if `ident = 01%2F02%2F0001.jp2` and in the config file:

```ini
[resolver]
impl = 'loris.resolver.SimpleFSResolver'
src_img_root=/usr/local/share/images
```

then `app.resolver.resolve(ident)` will return

```
/usr/local/share/images/01/02/0001.jp2
```

### `ExtensionNormalizingFSResolver`

This supplied implementation extends the SimpleFSResolver, adding an additional "extension map" feature. It allows multiple extensions to be associated with a single file format. If you only need to support "jpg", "tif", and "png" you won't need to use this resolver. If for example you need to support "tiff" and "jpeg" files, you could implement this config::

```ini
[resolver]
impl = 'loris.resolver.ExtensionNormalizingFSResolver'
src_img_root = '/usr/local/share/images'
  [[extension_map]]
  jpeg = 'jpg'
  tiff = 'tif'
```

### `SimpleHTTPResolver`

#### Main Configuration

This supplied implementation allows one to resolve identifiers against a HTTP source. This resolver requires a variable of "cache_root" be specified (the location to locally cache retrieved images) and that either "source_prefix" and/or "uri_resolvable" is configured.

A sample config of this resolver might be:

```ini
[resolver]
impl = 'loris.resolver.SimpleHTTPResolver'
source_prefix='https://<server>/fedora/objects/'
source_suffix='/datastreams/accessMaster/content'
cache_root='/usr/local/share/images/loris'
user='<if needed else remove this line>'
pw='<if needed else remove this line>'
```

Another sample configuration assuming one wishes to use uri's:

```ini
[resolver]
impl = 'loris.resolver.SimpleHTTPResolver'
uri_resolvable=True
cache_root='/usr/local/share/images/loris'
```

A full configuration sample that shows all the options and their defaults are:

```ini
[resolver]
impl = 'loris.resolver.SimpleHTTPResolver'
source_prefix=''
source_suffix=''
uri_resolvable=False
head_resolvable=False #DO set this to true if using Fedora Commons 3.8 or later. Earlier versions have a bug for a head response.
default_format=None #Set this if your HTTP server doesn't populate content-response. An example value might be "jp2".
ident_regex=False #Set this to a regular expression matching your identifier pattern to reduce unnecessary network traffic on source server
user=None
pw=None
cache_root='<must be configured>'
```

#### Required Other Configurations

Additionally, please note the following must also exist if the "enable_caching" is True and be configured to be owned by the loris user. While the cache_root above with the larger derivatives can be on a NAS, these following must likely be stored on the local server file system to avoid problems (they are somewhat small however):

```ini
[img.ImageCache]
cache_dp = '/var/cache/loris/img' # rwx
cache_links = '/var/cache/loris/links' # rwx

[img_info.InfoCache]
cache_dp = '/var/cache/loris/info' # rwx
```

#### Examples in the Wild

[https://www.digitalcommonwealth.org](https://www.digitalcommonwealth.org) - Used for all object images except thumbnails.

### `Creating Your Own`

See `resolver._AbstractResolver` for details. Note that any properties you add in the `[resolver.Resolver]` section will be in the `self.config` dictionary as long as you subclass `_AbstractResolver`.

* * *

Proceed to the [Run `setup.py`](setup.md) or go [Back to README](../README.md)
