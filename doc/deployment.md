Deployment
==========

These instructions assume:
 * The `WSGI` script is at `/var/www/loris/loris.wsgi`
 * Loris itself is at `/var/www/loris`
 * You'll be logging to `/var/log/loris`
 * You'll cache images at `/usr/local/loris/cache`

__Note:__ Do one of _Daemon Mode_ or _Embedded Mode_, and then go on to 
_Resolving Identifiers_ and _Cache Management_ .

Daemon Mode
-----------

 1. Make a user: `useradd -d /var/www/loris -s /sbin/false loris`
 1. Make the log directory: `mkdir /var/log/loris`
 1. Make the cace directory: `mkdir -p /usr/local/loris/cache`
 1. Clone loris to /var/www/loris `git@github.com:pulibrary/loris.git /var/www/loris` (or clone it elsewhere and move it, if that's easier).
 1. Adjust ownership: `chown -R loris:loris /var/www/loris /var/log/loris /usr/local/loris/cache`
 1. Create a simple wsgi script at `/var/www/loris/loris.wsgi`:

```python
#!/usr/bin/env python
import sys
sys.path.append('/var/www/loris/loris')

from app import create_app
application = create_app()

```

 1. Adjust `/var/www/loris/etc/loris.conf`:
   * set `cache_root` to `/usr/local/loris/cache`
 1. Adjust `/var/www/loris/etc/logging.conf`:
   * under `[handler_err]` and `[handler_out]` set args to reflect the correct log dir, .e.g. something like `args=('/var/log/loris/loris.err', 'midnight', 1, 14)`
   * you may want to adjust levels as well

1. Update your Apache VirtualHost:

```
AllowEncodedSlashes On # <--- Critical if you're using the default resolver!
WSGIDaemonProcess loris user=loris group=loris processes=5 threads=25 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi

<Directory /var/www/loris>
  WSGIProcessGroup loris
  WSGIApplicationGroup %{GLOBAL}
  Order allow,deny
  Allow from all
</Directory>
```

Embedded Mode
-------------

_TODO_ See: 
 * http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines#Defining_Process_Groups
 * http://code.google.com/p/modwsgi/wiki/ProcessesAndThreading

Resolving Identifiers
---------------------
See `loris/resolver.py`. It depends what you're going to do here, but with the default you're going to at least need to change the `SRC_IMG_ROOT` constant. It is assumed that different users in different environment will likely need to implmenent the `resolve` function in `resolver.py` in different ways. That said... 

The supplied method for resolving identifiers to images is about as simple as 
it could be. In a request that looks like this 

    http://example.edu/loris/some/img/dir/0004/0,0,256,256/full/0/color.jpg

The portion between the path the to service on the host server and the region, 
(excluding leading and trailings `/`s), i.e.:

    http://example.edu/loris/some/img/dir/0004/0,0,256,256/full/0/color.jpg
                             \_______________/

will be joined to the `SRC_IMG_ROOT` constant, and have `.jp2` appended. So if

    SRC_IMG_ROOT=/usr/local/share/images

then this file must exist:

    /usr/local/share/images/some/img/dir/0004.jp2 

According the the specification, [the identifier must be URL encoded] [9], but 
with the supplied implementation either will work, i.e. `some/img/dir/0004` or
`some%2Fimg%2Fdir%2F0004`. __Make sure `AllowEncodedSlashes` is set to `On` in
your Apache configuration.__ 

Cache Management
----------------
See `bin/cache_clean.sh`. This simple script can be configured and deployed as 
a cron job.
 1. Set LOG, CACHE_DIR, REDUCE_TO
 1. crontab -e -u loris ...
