Apache Deployment Notes
=======================

The following has been tested on Ubuntu 12.04 and 14.04. Other recipes, suggestions, clarifications, corrections welcome!

These instructions assume you have (or will) run `sudo ./setup.py install` with the default configurations options.

You can get all of the dependencies from apt:

```
$ sudo apt-get install apache2 libapache2-mod-wsgi
```

Next enable to require modules:

``
sudo a2enmod headers expires
``

Next edit the site configuration file `/etc/apache2/sites-enabled/000-default.conf` with your editor of choice (you'll need root privileges; the name may be different; if there is no site symlinked in the directory, enable the site with, for example `a2ensite 000-default.conf`).

Now add something to this affect:

```
ExpiresActive On
ExpiresDefault "access plus 5184000 seconds"

AllowEncodedSlashes On

WSGIDaemonProcess loris2 user=loris group=loris processes=10 threads=15 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris2/loris2.wsgi
WSGIProcessGroup loris2
```

Explanation:

 * `ExpiresActive On` and `ExpiresDefault` sets the `Cache-Control` and `Expires` headers, e.g. with the setting above responses will include (assuming I made the request at `Sat, Nov 23 2013 19:45:20 GMT`):

 ```
 < Cache-Control: max-age=5184000
 < Expires: Wed, 22 Jan 2014 19:45:20 GMT
 ```

 5184000 = 60 days.

 (Loris is setting the `Last-Modified` header based on the file system metadata.)

 * `AllowEncodedSlashes On` lets `%2F` though in requests (they're allowed but must be escaped in the identifier portion of the URI). Depending on your hosting environment, this may need to be explicitly declared *inside* a VirtualHosts container as `AllowEncodedSlashes` is not inherited by VirtualHosts if declared in a global context (see [Apache Bug 46830](https://bz.apache.org/bugzilla/show_bug.cgi?id=46830)).

 * WSGI Flags. Have a look at the [mod-wsgi configuration guidelines](https://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines). In general is seems like a good idea to prefer threads over processes; ([check out this answer on serverfault](http://serverfault.com/a/146382)).

 If you would like Loris's access logs to be kept in a separate file you can add:

 ```
 SetEnvIf Request_URI ^/loris loris
 CustomLog ${APACHE_LOG_DIR}/loris-access.log combined env=loris
 ```

The first argument to `SetEnvIf Request_URI` should match the first argument to `WSGIScriptAlias` above, plus a leading `^`.

On RedHat only you'll likely need to add:

```
WSGISocketPrefix /var/run/wsgi
```

as well. See: [Location of Unix Sockets](http://code.google.com/p/modwsgi/wiki/ConfigurationIssues#Location_Of_UNIX_Sockets).

Finally, restart Apache and have a look (start at http://{your_server}/loris).

* * *

Proceed to [Developer Notes](develop.md) (optional) or go [Back to README](../README.md)
