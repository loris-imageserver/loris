NGINX and uWSGI Deployment Notes
=======================

The following has been tested on a Python 3.7.3 virtual environment on CentOS7.

These instructions assume you have (or will) run `sudo ./setup.py install` with the default configurations options.

Instructions on how to install NGINX on your system can be found [here](https://www.nginx.com/resources/wiki/start/topics/tutorials/install/).

Install the uWSGI package:

```
pip install uwsgi
```

We'll now create a separate configuration file just for Loris. Create a new file inside the /etc/nginx/conf.d folder; name it `loris.conf` . Open it with your editor of choice, and put this code inside it:

```
server {
        listen 80;
        listen [::]:80;
        server_name www.example.com;
                
        location /loris {

          proxy_pass http://127.0.0.1:8888/;
        }
}
```

Locate the NGINX configuration file; on CentOS it's in /etc/nginx/nginx.conf. Open it with your editor of choice.

Just before the closing of the last '}' bracket, add:

```
    include loris.conf;
```

This will load the reverse-proxy configuration stored in the loris.conf you created.

Create a new file called `loris.wsgi` and place it, for instance, inside the `/var/www/loris2` folder. Open it with your editor of choice, and populate it with the following code:

```
#!/your/python/path python
#-*- coding: utf-8 -*-

from loris.webapp import create_app
application = create_app(debug=False, config_file_path='/root/python_ve/loris/etc/loris2.conf')
```

Now create a new file called `uwsgi.ini` and place it wherever you want. Its content will be:

```
[uwsgi]
http-socket = :8888
processes = 16
wsgi-file = /var/www/loris2/loris.wsgi # or wherever your loris.wsgi is.
```

Now you're ready to launch your application:

```
uwsgi --ini /root/python_ve/loris/uwsgi.ini --master --enable-threads
```

For more information about Python/WSGI application, with extended documentation on the uWSGI module, see [here](https://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html).

Finally, restart NGINX (`systemctl restart nginx on CentOS7`) and have a look (start at http://{your_server}/loris). Hopefully you'll be greeted with this nice message:

```
This is Loris, an image server that implements the IIIF Image API Level 2. See
<http://iiif.io/api/image/2.0/> for details and <https://github.com/loris-imageserver/loris>
for the source code and implementation details.
```

* * *

Proceed to [Developer Notes](develop.md) (optional) or go [Back to README](../README.md)
