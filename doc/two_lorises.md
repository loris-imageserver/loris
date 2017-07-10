# VirtualEnv Configuration for Running Multiple Lori(-ses?)

See https://code.google.com/p/modwsgi/wiki/VirtualEnvironments

This assumes you'll create virtual environment in a user's home directory, and
use those environments to store the different dependencies for each version.

The system Python is still used to run WSGI, though it may be possible to use 
different versions of Python using the `WSGIPythonHome` directive (untested).

## Basic Setup:

```
mkdir ~/src
mkdir ~/virtualenvs
```

Make the new environments:

```
virtualenv --no-site-packages ~/virtualenvs/loris1
virtualenv --no-site-packages ~/virtualenvs/loris2
```

## Install Loris 1

```
cd ~/virtualenvs/loris1
source bin/activate
```

Get the source for the last 1.x.x release
```
cd ~/src
wget https://github.com/pulibrary/loris/archive/1.2.3.tar.gz
tar xzvf 1.2.3.tar.gz
cd ~/src/loris-1.2.3
pip install -r requirements.txt --use-mirrors
```

Configure whatever you need, (_cache directories __SHOULD NOT__ be shared_) then:

```
sudo ~/virtualenvs/loris1/bin/python setup.py install
```

Deactiveate the virtualenv

```
deactivate
```

To /var/www/loris/loris.wsgi, add:

```
# CHANGE /home/jstroop to whatever...
import site
site.addsitedir('/home/jstroop/virtualenvs/loris1/lib/python2.7/site-packages')
```

To the Apache vhost:

```
# Loris 1
AllowEncodedSlashes On
WSGIDaemonProcess loris user=loris group=loris processes=5 threads=5 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi
WSGIProcessGroup loris
```

You may want to tweak your logging configuration as well!


## For Loris 2

```
cd ~/virtualenvs/loris2
source bin/activate
```

Get the source for the latest 2.x.x release:

```
cd ~/src
wget https://github.com/pulibrary/loris/archive/2.0.0-alpha2.tar.gz
tar xzvf 2.0.0-alpha2.tar.gz
cd ~/src/loris-2.0.0-alpha2
pip install -r requirements.txt --use-mirrors
```

Configure whatever you need, (_cache directories __SHOULD NOT__ be shared_) then:

```
sudo ~/virtualenvs/loris2/bin/python setup.py install
```

Deactiveate the virtualenv:

```
deactivate
```

To /var/www/loris/loris2.wsgi, add:

```
# CHANGE /home/jstroop to whatever...
import site
site.addsitedir('/home/jstroop/virtualenvs/loris2/lib/python2.7/site-packages')
```

To the Apache vhost:
```
# Loris 2
AllowEncodedSlashes On
WSGIDaemonProcess loris2 user=loris group=loris processes=5 threads=5 maximum-requests=10000
WSGIScriptAlias /loris2 /var/www/loris/loris2.wsgi
WSGIProcessGroup loris2
```
