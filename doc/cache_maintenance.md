Caching
=======

There is a Bash script at [`bin/loris-cache_clean.sh`](bin/loris-cache_clean.sh) that makes heavy use of `find` command line utility to turn the filesystem cache into a simple LRU-style cache. Have a look at it and set the constants near the top; it is intended to be deployed as a cron job.

After you run `setup.py install` this script will be a `/usr/local/bin/loris-cache_clean.sh`.

* * *

Proceed to the [Resolver Instructions](resolver.md) or go [Back to README](README.md)
