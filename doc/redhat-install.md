Install on Red Hat (CentOS)
===========================

Installing Loris on Red Hat Enterprise Linux 6 (or the equivalent CentOS
system) is tricky, since the bundled Python is not the right version and none
of the `yum` packages are the latest versions. This guide is an attempt to
guide you through the install process.

Everything here needs to be done as root, so either open a root shell now or
precede all instructions here with `sudo`. It also assumes you have `yum`,
`wget`, and `git` in your path already (you may need to install git).

Install Python 2.7
------------------

The first thing to do is to install Python 2.7 (RHEL 6 ships with 2.6). To do
that, first you have to install the development tools (a C compiler and
associated tools). Then we'll need a handful of other libraries so that we can
compile Python itself.

```
yum groupinstall "Development tools"
yum install zlib-devel bzip2-devl openssl-devel ncurses-devel \
    sqlite-devel readline-devel tk-devel
```

Once that's done, we can get the Python source and install it somewhere. The
rest of this document assumes you're installing to `/usr/local`, but you can
do it wherever you like; just change the `--prefix` option when you configure
python. Note that `--enable-shared` must be passed, otherwise we won't be
able to use this Python under mod_wsgi. Also note the `altinstall`, running
just `make install` won't cut it.

```
wget http://python.org/ftp/python/2.7.3/Python-2.7.3.tar.bz2
tar xf Python-2.7.3.tar.bz2
cd Python-2.7.3
./configure --prefix=/usr/local --enable-shared
make && make altinstall
```

Once that's done you need to put the shared libraries somewhere where the
system can find them.

```
echo "/usr/local/lib/python2.7" > /etc/ld.so.conf.d/python27.conf
echo "/usr/local/lib" >> /etc/ld.so.conf.d/python27.conf
ldconfig
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
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
/usr/local/bin/python2.7 get-pip.py
```

Install mod_wsgi
----------------

Because mod_wsgi has to be compiled with the Python we want to use (2.7),
you'll need to compile it from source yourself. Make sure you pass the correct
path to your new Python installation to the configure script. (I'm not sure
whether you can run multiple mod_wsgi versions simultaneously; my gut says no).

```
wget http://modwsgi.googlecode.com/files/mod_wsgi-3.4.tar.gz
tar -zxf mod_wsgi-3.4.tar.gz
cd mod_wsgi-3.4
./configure --with-python=/usr/local/bin/python2.7
make && make install
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

Loris ships with Kakadu version Version 7.2 which is compiled with glibc 2.14, 
and Red Hat only has version 2.12. This means that the bundled `kdu_expand` program 
won't work at all. Fortunately we can get an older version from Github. These are 
the 64-bit versions; if you need 32-bit change the portion of the URL from `x86-64` 
to `x86-32`.

```
wget https://github.com/ksclarke/freelib-djatoka/tree/master/lib/Linux-x86-32/libkdu_v60R.so
wget https://github.com/ksclarke/freelib-djatoka/tree/master/lib/Linux-x86-32/kdu_expand

mv libkdu_v60R.so /usr/local/lib
mv kdu_expand /usr/local/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
```

This earlier version of Kakadu does not support JPEG2000 images in colorspaces other 
that those allowed by an earlier version of the JPEG2000 specification. Chances are very good
that this won't be a problem for you, but you should disable the [`map_profile_to_srgb`](https://github.com/pulibrary/loris/blob/development/etc/loris.conf#L66) feature just in case.


Install pip dependencies
------------------------

This part is easy. You'll want to make sure you use the correct pip (probably
at `/usr/local/bin/pip2.7`), and that Pillow builds properly. See the main
install notes for details...if you've done everything correctly up to now you
should have no problems.

```
/usr/local/bin/pip2.7 install Werkzeug
/usr/local/bin/pip2.7 install Pillow
```

Install Loris
-------------

Now you're ready to install Loris proper. This is usually a matter of `git clone`ing 
this repo, adding the loris user, and running `setup.py`. The only
caveat here is that you must be sure to install using Python 2.7.

Note that if you run `test.py` that things will probably fail since it tries to
use the bundled Kakadu libraries by default. You can fix this by removing the
relevant libraries inside of your cloned git repo and copying the binary/libray
you downloaded above into the correct places.

```
useradd -d /var/www/loris -s /sbin/false loris
git clone https://github.com/pulibrary/loris.git
cd loris

# (configure as necessary)

/usr/local/bin/python2.7 setup.py install
```

At this point you'll want to go through everything else suggested in the main
install script: configuring Apache and whatnot.

Fix permissions
---------------

This is by far the most tedious part of getting Loris installed correctly.
Because Red Hat uses SELinux extra permissions, the odds are very high that
you'll wind up with a bunch of "Permission denied" errors when you try to run
it.

(Details follow...you can skip the next two paragraphs if you just want to fix
it and don't care why).

This happens even when Loris is set up under mod_wsgi to run as user/group
`loris`. The problem arises when trying to open a named pipe, aka a fifo, in
`/tmp/loris/tmp/jp2` (or wherever you've configured it), even though that
directory is owned by loris. The issue is that the `httpd` process doesn't have
permissions to deal with FIFOs by default, even in directories that it owns.
The relevant Python code is in `loris/transforms.py`, in the method
`KakaduJP2Transformer.transform()`.

I have a hunch that you could get around this particular security restriction
by patching the code to write to a file, then reading from the file, rather
than from a named pipe. This would probably impact performance a great deal,
though, since the whole process would have to stop while `kdu_expand` did its
work completely.

(Skimmers should start reading again.)

The fix is to create a custom security module that you load into Red Hat to
allow httpd permissions to deal with fifos. You'll want to copy this into a
file called `httpd_local.te` (at any rate, make sure the file name matches the
module name in the first line).

```
module httpd_local 1.0;

require {
    type httpd_tmp_t;
    type httpd_t;
    type user_home_dir_t;
    class dir getattr;
    class fifo_file { open write getattr setattr read create unlink };
}

#============= httpd_t ==============
allow httpd_t httpd_tmp_t:fifo_file { open write getattr setattr read create unlink };
```

Then, you'll need to create a `.mod` file and compile it into the policy module
itself a `.pp` file).

```
checkmodule -M -m -o httpd_local.mod httpd_local.te     # create mod file
semodule_package -m httpd_local.mod -o httpd_local.pp   # compile it
semodule -i httpd_local.pp                              # install it
```

If all goes well, everything *should* be working properly!
