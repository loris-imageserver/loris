Run `setup.md`
==============

You should have the tests passing by now, and have `loris/etc/loris.conf` set the way you want it.

Now create a user that will own the loris application, e.g.:

```
$ useradd -d /var/www/loris -s /sbin/false loris
```

This user needs to match the `run_as_user` and `run_as_group` options of in the `[loris.Loris]` section of `etc/loris.conf`.

Finally, from the `loris` (not `loris/loris`) directory, either as root or with `sudo` run `./setup.py install`.

* * *

Proceed to [Deploy with Apache](apache.md) or go [Back to README](README.md)
