Install on Red Hat (CentOS) 7
=============================

Everything here needs to be done as root, so either open a root shell now or
precede all instructions here with `sudo`.

Install Dependencies
--------------------

 * mod_wsgi for apache
 * python-devel for `pip install Pillow`
 * bzip2 for library installed via Loris' `python setup.py install`

```
yum install git wget mod_wsgi python-devel bzip2
```

Install pip
-----------

At this point, you should have a `python2.7` binary in your `$PATH` somewhere
(probably at `/usr/local/bin/python2.7`). We need to install pip so we can get
the necessary dependencies for Loris. That's pretty simple: follow the
instructions on the [pip wesite](http://www.pip-installer.org/en/latest/installing.html).
Make sure you run the script with the correct Python or pip will install
packages to the wrong place.

```
cd /opt
wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
```

Install image libraries
-----------------------

Next you'll need to install all the necessary image libraries so that loris
will work properly. You can get what you need through yum:

```
yum install libjpeg-turbo libjpeg-turbo-devel \
    freetype freetype-devel \
    zlib-devel \
    libtiff-devel
```


Install pip dependencies
------------------------

```
pip install Werkzeug
pip install Pillow
```

Install Loris
-------------

```
useradd -d /var/www/loris -s /sbin/false loris
git clone https://github.com/pulibrary/loris.git
cd loris

# (configure as necessary)

python setup.py install
```

At this point you'll want to go through everything else suggested in the main
install script: [configuring Apache](apache.md) and whatnot.

After apache is configured, you can test by adding an image to `/usr/local/share/images` and visit a URL like:

`http://{YOUR SERVER NAME}/loris/{YOUR TEST FILE NAME}/full/full/0/default.jpg`



SELinux module
---------------

If SELinux is enabled you will need to create a custom security module that you load into Red Hat to
allow httpd permissions to write to cache. You'll want to copy this into a
file called `loris.te` (at any rate, make sure the file name matches the
module name in the first line).

```
module loris 1.0;

require {
        type httpd_t;
        type var_t;
        class file { write read getattr open };
}

#============= httpd_t ==============
allow httpd_t var_t:file { write read getattr open };
```

Then, you'll need to create a `.mod` file and compile it into the policy module
itself a `.pp` file).

```
checkmodule -M -m -o loris.mod loris.te     # create mod file
semodule_package -m loris.mod -o loris.pp   # compile it
semodule -i loris.pp                              # install it
```

If all goes well, everything *should* be working properly!
