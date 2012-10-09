Deployment
==========

These instructions assume:
 * The `wsgi` script is at `/var/www/loris/loris.wsgi`
 * Loris itself is at `/var/www/loris`
 * You'll be logging to `/var/log/loris`
 * You'll cache images at `/usr/local/loris/cache`

Do one of _Daemon Mode_ or _Embedded Mode_, and then go on to Cache Management.

Daemon Mode
-----------

 1. Make a user: `useradd -d /var/www/loris -s /sbin/false loris`
 1. Make the log directory: `mkdir /var/log/loris`
 1. Make the cace directory: `mkdir -p /usr/local/loris/cache`
 1. Clone loris to /var/www/loris `git@github.com:pulibrary/loris.git /var/www/loris` (or clone it elsewhere and move it, if that's easier).
 1. Adjust ownership: `chown loris:loris /var/www/loris /var/log/loris /usr/local/loris/cache`
 1. Create a simple wsgi script at `/var/www/loris/loris.wsgi`:

```python
#!/usr/bin/env python
import sys; 
sys.path.append('/var/www/loris')

from loris import create_app
application = create_app()

```

 1. Adjust `/var/www/loris/loris.conf`:
   * set `cache_root` to `/usr/local/loris/cache`
   * under `[handler_err]` and `[handler_out]` set args to reflect the correct log dir, .e.g. something like `args=('/var/log/loris/loris.err', 'midnight', 1, 14)`
   * you may want to adjust levels as well

1. Adjust `resolver.py`. It depends what you're going to do here (see `README`), but with the default you're going to at least need to change the `SRC_IMG_ROOT` constant.

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

Cache Management
----------------
See `bin/cache_clean.sh`. This simple script can be configured and deployed as a cron.
