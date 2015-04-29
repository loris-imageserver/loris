Caching
=======

### `SimpleFSResolver` and `SimpleHTTPResolver`

There are two a Bash scripts at `bin/loris-cache_clean.sh` and `bin/loris-http_cache_clean.sh` that makes heavy use of `find` and `du` command line utilities to turn the filesystem cache into a simple LRU-style cache. Have a look at it and set the constants near the top; it is intended to be deployed as a cron job.

__`setup.py` will not move or deploy the script for you.__ You can do this with, e.g. `sudo crontab -e -u loris` (replace `loris` with a user that has permission to delete files from the cache).

`du` can take a very long time to run if you've configured your cache to be very large. In this case, consider setting an arbitrarily high disk usage quota for the cache owner ('arbitrarily high' so that you don't get errors if you go over a bit between executions of the cron script), and replace the `current_usage()` function in the cron script with:

```bash
current_usage () {
	quota -Q -u loris |grep sdc1 | awk '{ print $2 }'
}
```

* * *

Proceed to the [Resolver Instructions](resolver.md) or go [Back to README](../README.md)
