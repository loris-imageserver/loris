# /usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py

from ConfigParser import ConfigParser
from grp import getgrnam
from pwd import getpwnam
from setuptools import setup
from distutils.sysconfig import get_python_lib
from sys import stderr, stdout, exit
import loris
import os

VERSION = loris.__version__
LOG_DP = '/var/log/loris' # if you change this, change it in log_config.py too!
ETC_DP = '/etc/loris'
BIN_DP = '/usr/local/bin'
LORIS_CACHE_CLEAN = os.path.join(BIN_DP, 'loris-cache_clean.sh')
RMDIRS_SH = 'rmdirs.sh'

this_dp = os.path.abspath(os.path.dirname(__file__))

# Get the config file
conf_fp = os.path.join(this_dp, 'etc', 'loris.conf')
conf = ConfigParser()
conf.read(conf_fp)

# Make sure the ultimate owner of the app exists before we go any further
try:
	user_n = conf.get('loris.Loris', 'run_as_user')
	group_n = conf.get('loris.Loris', 'run_as_group')
	user = getpwnam(user_n)
	group = getgrnam(group_n)
	user_id = user.pw_uid
	group_id = group.gr_gid
except KeyError:
	msg = '''
User "%s" and or group "%s" do(es) not exist.
Please create this user, e.g.:
	`useradd -d /var/www/loris -s /sbin/false loris`

'''% (user_n,group_n)
	stderr.write(msg)
	exit(67)


cache_dp = conf.get('img.ImageCache', 'cache_dp')
cache_links = conf.get('img.ImageCache', 'cache_links')
info_cache_dp = conf.get('img_info.InfoCache', 'cache_dp')
www_dp = conf.get('loris.Loris', 'www_dp')
tmp_dp = conf.get('loris.Loris', 'tmp_dp')


# If all of that worked, determine requirements
install_requires = []
try:
	import werkzeug
except ImportError:
	install_requires.append('werkzeug>=0.8.3')
	
data_files=[
	(ETC_DP, ['etc/loris.conf']),
	(BIN_DP, ['bin/loris-cache_clean.sh']),
	(LOG_DP, []),
	(cache_dp, []),
	(cache_links, []),
	(info_cache_dp, []),
	(www_dp, ['www/loris.wsgi']),
	(www_dp, ['www/index.txt']),
	(tmp_dp, []),
]

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name='Loris',
	author='Jon Stroop',
	author_email='jstroop@princeton.edu',
	url='https://github.com/pulibrary/loris',
	description = ('IIIF Image API 1.1 Level 2 compliant Image Server'),
	long_description=read('README.md'),
	license='GPL',
	version=VERSION,
	packages=['loris'],
	install_requires=install_requires,
	data_files=data_files,
)

loris_dirs = list(set([n[0] for n in data_files if n[0] != BIN_DP]))

# Change permissions for all the new dirs to Loris's owner.
for fs_node in loris_dirs:
	os.chown(fs_node[0], user_id, group_id)
	os.chmod(fs_node[0], 0755)

os.chmod(LORIS_CACHE_CLEAN, 0755)
os.chown(LORIS_CACHE_CLEAN, user_id, group_id)

wsgi_script = os.path.join(www_dp, 'loris.wsgi')
os.chmod(wsgi_script, 0755)
os.chown(wsgi_script, user_id, group_id)

index = os.path.join(www_dp, 'index.txt')
os.chmod(index, 0644)
os.chown(wsgi_script, user_id, group_id)


parent_loris_dirs = [os.path.dirname(d) for d in loris_dirs \
	if os.path.basename(os.path.dirname(d)) == 'loris']

to_rm = list(set(loris_dirs + parent_loris_dirs))
to_rm.sort(reverse=True)

# Make a script to help with removing dirs.
s = '''#!/bin/sh

# Removes all directories created by running loris/setup.py, HOWEVER, the 
# packages themselves, probably in `%s` or wherever your 
# system put them will not be removed and easy-install.pth will not be altered. 
# If you don't know where these are, consider running `setup.py` with 
# `--record files.txt` appended, which will log what it did.

''' % (get_python_lib(),)

rmdirs_script = [s]
rmdirs_script += ['rm -r %s\n' % (n,) for n in to_rm]
rmdirs_script.append('rm %s\n' % (LORIS_CACHE_CLEAN,))
rmdirs_script.append('\n')
with open(RMDIRS_SH,'wb') as f:
	f.write(''.join(rmdirs_script))
os.chmod(RMDIRS_SH, 0744)


todo = '''
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
Installation was successful. Here's where things are:

 * Loris configuration: %(config)s
 * Cache cleaner cron: %(cache_clean)s
 * Logs: %(logs)s
 * Image cache (opaque): %(cache_dp)s
 * Image cache (symlinks that look like IIIF URIs): %(cache_links)s
 * Info cache: %(info_cache_dp)s
 * WSGI application directory: %(www_dp)s
 * Temporary directory: %(tmp_dp)s

However, you have more to do. See README.md and doc/deployment.md for details. 
In particular:

 0. You should have read README.md already, and know what I'm talking about.

 1. Double check that the kakadu libraries and executable are where you said 
    they'd be in the config file (etc/loris.conf, now at %(config)s).

 2. Make sure that the Python Imaging Library is installed and working. See 
    notes about this in README.md.

 3. Configure the cron job that manages the cache (bin/loris-cache_clean.sh, 
    now at %(cache_clean)s). Make sure the constants match 
    how you have Loris configured, and then set up the cron 
    (e.g. `crontab -e -u %(user_n)s`).

 4. Have a look at the WSGI file in %(www_dp)s. It should be fine as-is, but 
    there's always a chance that it isn't. The first thing to try is explictly
    adding the package to your PYTHONPATH (see commented code).

 5. Configure Apache.

Note also that a script for removing all of the directories that were made for 
loris, except for the packages themselves, has been created at %(rm_dirs)s in 
case you need to start over. Have a look before you run it though.

Cheers! -Js
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
''' % {
	'config' : ETC_DP,
	'cache_clean' : LORIS_CACHE_CLEAN,
	'user_n' : user_n,
	'rm_dirs': RMDIRS_SH,
	'logs' : LOG_DP,
	'cache_dp' : cache_dp,
	'cache_links' : cache_links,
	'info_cache_dp' : info_cache_dp,
	'www_dp' : www_dp,
	'tmp_dp' : tmp_dp
}

stdout.write(todo)