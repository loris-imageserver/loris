# Installing Loris on a Python virtual environment and Apache mod_wsgi on Oracle 7.x.

The instructions below assume that you're logged in as root. If you're not, use `sudo` where applicable.  
They also assume that your SELinux module is set to 'permissive' or 'disabled' (in `/etc/sysconfig/selinux`). If it's enabled you might have some issues with Loris not being able to write cache and temporary files.

## Apache

```
yum install httpd
apachectl start
systemctl enable httpd

firewall-cmd --permanent --zone=public --add-service=http
firewall-cmd --reload
```

## Loris dependencies

```
yum install deltarpm # optimises update processes
yum update # at least twice, until it returns 'No packages marked for update'. Let's make sure we have all the up-to-date packages.

yum-config-manager --enable *optional_latest # this is for making libwebp-devel available
yum install python-setuptools zlib-devel freetype libjpeg-turbo-devel openjpeg2 lcms2-utils nano libtiff-devel libwebp-devel openjpeg2 gcc python3 git httpd-devel python3-devel wget
```

## OpenJPEG (In case you need these libraries)

```
wget https://github.com/uclouvain/openjpeg/releases/download/v2.4.0/openjpeg-v2.4.0-linux-x86_64.tar.gz
tar -xzvf openjpeg-v2.4.0-linux-x86_64.tar.gz 
cp openjpeg-v2.4.0-linux-x86_64/bin/* /usr/bin/
cp -fR openjpeg-v2.4.0-linux-x86_64/lib/* /usr/lib/
```

## Python3 virtual environment.
Here we are using the Python3 available with yum. If you want to use another Python 3 package then of course do install it via source code before proceeding with the next steps.

Change to a directory where you want to put the environment. Here we are using /usr/local/ .

`python3 -m venv python3_venv`

To activate that environment and therefore make sure you install all the packages locally and not globally:

```
source python3_venv/bin/activate
which python # This must return ../python3_venv/bin/python
python --version # This must retun 3.X
```

## Loris and its Python dependencies [make sure the virtual environment is active]

```
pip install --upgrade pip setuptools
pip install Pillow
```

We add the loris user, which will be the user Loris will run with.  
`adduser loris`

Go to the directory you want to put Loris source code in (in our case /usr/local/)

```
git clone https://github.com/loris-imageserver/loris.git
cd loris
./setup.py install
./bin/setup_directories.py
chown -fR loris /tmp/loris
chown -fR loris /var/cache/loris
ln -s /usr/local/python3_venv/lib/python3.6/site-packages/Loris-3.2.1-py3.6.egg/loris/data/loris.conf /etc/loris.conf # This is for accessing the configuration file from /etc without going to (and having to remember) that long path.
```

## Install and configure the local mod_wsgi (this is not system-wide: this only belongs to your virtual environment. See [here](https://modwsgi.readthedocs.io/en/master/user-guides/virtual-environments.html) for more details.)

```
pip install wheel mod_wsgi

mod_wsgi-express module-config # copy the output of this command ...
nano /etc/httpd/conf.modules.d/00-wsgi.conf # ... and paste it in this file you're going to create. Now Apache is loading the mod_wsgi compiled and installed with/in the Python virtual environment
```

## To deactivate the virtual environment:

`deactivate`

## Apache configuration

`nano /etc/httpd/conf.d/loris.conf`

```
ExpiresActive On
ExpiresDefault "access plus 5184000 seconds"

AllowEncodedSlashes On

WSGIDaemonProcess loris user=loris group=loris processes=10 threads=15 maximum-requests=10000
WSGIScriptAlias /loris /var/www/loris/loris.wsgi
WSGIProcessGroup loris
```

Note: if your're using Python 3.8+ the WSGIScriptAlias line must be:

`WSGIScriptAlias /loris /var/www/loris/loris.wsgi process-group=loris application-group=%{GLOBAL}`

See [here](https://github.com/loris-imageserver/loris/blob/development/doc/apache.md) for more details.

`nano /var/www/loris/loris.wsgi`

```
## uncomment and edit:
import site
site.addsitedir('/usr/local/python3_venv/lib/python3.6/site-packages')
```

## If you're using Kakadu libraries

Change these two paths in `/etc/loris.conf`:

```
[[JP2]]
[...]
kdu_expand = '/usr/local/loris/bin/Linux/x86_64/kdu_expand' # r-x
kdu_libs = '/usr/local/loris/lib/Linux/x86_64/' # r--
```

## If you're using OpenJPEG libraries

Change these two paths in `/etc/loris.conf`:

```
[[JP2]]
[...]
opj_decompress = '/usr/bin/opj_decompress' # r-x
opj_libs = '/usr/lib' # r--
```

See [here](https://github.com/loris-imageserver/loris/blob/development/doc/apache.md) for more information for deploying Loris with Apache, including a note for Python3.8+ users.

## Restart Apache every time the configuration changes:

`systemctl restart httpd`
