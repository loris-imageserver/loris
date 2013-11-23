Resolving Identifiers
=====================

The supplied implementation just unescapes the identifier and tacks a constant path onto the front. e.g. if `ident = 01%2F02%2F0001.jp2` and in the config file:

```ini
[resolver.Resolver] 
src_img_root=/usr/local/share/images
```

then `app.resolver.resolve(ident)` will return 

```
/usr/local/share/images/01/02/0001.jp2
```

You'll probably want to do something smarter. See `resolver._AbstractResolver` for details. Note that any properties you add in the `[resolver.Resolver]` section will be in the `self.config` dictionary as long as you subclass `_AbstractResolver`.

* * *

Proceed to the [Run `setup.py`](doc/setup.md) or go [Back to README](README.md)
