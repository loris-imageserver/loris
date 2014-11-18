#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py

EX_NOUSER = 67
EX_TEMPFAIL = 75
BIN_DP = '/usr/local/bin'
ETC_DP = '/etc/loris'
LIB_DP = '/usr/local/lib'

from sys import stderr, stdout, exit
from grp import getgrnam
from pwd import getpwnam
from setuptools import setup
from distutils.sysconfig import get_python_lib
import loris
import os
from loris.constants import CONFIG_FILE_NAME

try:
	from configobj import ConfigObj
except ImportError:
	msg = '''
configobj <http://www.voidspace.org.uk/python/configobj.html> is required before
setup.py can be run. Please do (with sudo if necessary):

$ pip install configobj

and then run setup again.
'''
	stderr.write(msg)
	exit(EX_TEMPFAIL)
		
VERSION = loris.__version__

LORIS_CACHE_CLEAN = os.path.join(BIN_DP, 'loris-cache_clean.sh')
LORIS_HTTP_CACHE_CLEAN = os.path.join(BIN_DP, 'loris-http_cache_clean.sh')

this_dp = os.path.abspath(os.path.dirname(__file__))

# Get the config file
config_fp = os.path.join(this_dp, 'etc', CONFIG_FILE_NAME)
config = ConfigObj(config_fp, unrepr=True, interpolation=False)

# Make sure the ultimate owner of the app exists before we go any further
try:
	user_n = config['loris.Loris']['run_as_user']
	group_n = config['loris.Loris']['run_as_group']
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
	exit(EX_NOUSER)


cache_dp = config['img.ImageCache']['cache_dp']
cache_links = config['img.ImageCache']['cache_links']
info_cache_dp = config['img_info.InfoCache']['cache_dp']
www_dp = config['loris.Loris']['www_dp']
tmp_dp = config['loris.Loris']['tmp_dp']
log_dp = config['logging']['log_dir']

# If all of that worked, determine requirements
install_requires = []
try:
	import werkzeug
except ImportError:
	install_requires.append('werkzeug>=0.8.3')

data_files = [
	(ETC_DP, [os.path.join('etc', CONFIG_FILE_NAME)]),
	(log_dp, []),
	(cache_dp, []),
	(cache_links, []),
	(info_cache_dp, []),
	(www_dp, ['www/loris2.wsgi']),
	(www_dp, ['www/index.txt']),
	(tmp_dp, [])
]

JP2_EXECUTABLE = None
JP2_LIBS = None

if config['transforms']['jp2']['impl'] == 'KakaduJP2Transformer':
	from loris.transforms import KakaduJP2Transformer 
	JP2_EXECUTABLE = os.path.join(BIN_DP, 'kdu_expand')
	JP2_LIBS = os.path.join(LIB_DP, KakaduJP2Transformer.libkdu_name())
	data_files.append( (LIB_DP, [KakaduJP2Transformer.local_libkdu_path()]) )
	kdu_expand = KakaduJP2Transformer.local_kdu_expand_path()
	data_files.append( (BIN_DP, ['bin/loris-cache_clean.sh', 'bin/loris-http_cache_clean.sh', 'bin/iiif_img_info', kdu_expand]) )

elif config['transforms']['jp2']['impl'] == 'OPJ_JP2Transformer':
	from loris.transforms import OPJ_JP2Transformer
	JP2_EXECUTABLE = os.path.join(BIN_DP, 'opj_decompress')
	JP2_LIBS = os.path.join(LIB_DP, OPJ_JP2Transformer.libopenjp2_name())
	data_files.append( (LIB_DP, [OPJ_JP2Transformer.local_libopenjp2_path()]) )
	opj_decompress = OPJ_JP2Transformer.local_opj_decompress_path()
	data_files.append( (BIN_DP, ['bin/loris-cache_clean.sh', 'bin/loris-http_cache_clean.sh', 'bin/iiif_img_info', opj_decompress]) )

def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name='Loris',
	author='Jon Stroop',
	author_email='jpstroop@gmail.com',
	url='https://github.com/pulibrary/loris',
	description = ('IIIF Image API 2.0 Level 2 compliant Image Server'),
	long_description=read('README.md'),
	license='GPL',
	version=VERSION,
	packages=['loris'],
	install_requires=install_requires,
	data_files=data_files,
	test_suite = 'tests'
)

loris_owned_dirs = list(set([n[0] for n in data_files]))
loris_owned_dirs.remove(LIB_DP)
loris_owned_dirs.remove(BIN_DP)

# Change permissions for all the new dirs to Loris's owner.
for fs_node in loris_owned_dirs:
	os.chmod(fs_node, 0755)
	os.chown(fs_node, user_id, group_id)

wsgi_script = os.path.join(www_dp, 'loris2.wsgi')
executables = (LORIS_CACHE_CLEAN, LORIS_HTTP_CACHE_CLEAN, JP2_EXECUTABLE, wsgi_script)
for ex in executables:
	os.chmod(ex, 0755)
	os.chown(ex, user_id, group_id)

index = os.path.join(www_dp, 'index.txt')
os.chmod(index, 0644)
os.chown(index, user_id, group_id)

d = {
	'cache_clean' : LORIS_CACHE_CLEAN,
    'cache_http_clean' : LORIS_HTTP_CACHE_CLEAN,
	'cache_dp' : cache_dp,
	'cache_links' : cache_links,
	'config' : ETC_DP,
	'info_cache_dp' : info_cache_dp,
	'jptoo_exe' : JP2_EXECUTABLE,
	'jptoo_lib' : JP2_LIBS,
	'logs' : log_dp,
	'tmp_dp' : tmp_dp,
	'user_n' : user_n,
	'www_dp' : www_dp
}

todo = '''
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
Installation was successful. Here's where things are:

 * Loris configuration: %(config)s
 * Cache cleaner Simple cron: %(cache_clean)s
 * Cache cleaner HTTP cron: %(cache_http_clean)s
 * JP2 executable: %(jptoo_exe)s (kdu_expand or opj_decompress)
 * JP2 libraries: %(jptoo_lib)s (libkdu or libopenjp2)
 * Logs: %(logs)s
 * Image cache (opaque): %(cache_dp)s
 * Image cache (symlinks that look like IIIF URIs): %(cache_links)s
 * Info cache: %(info_cache_dp)s
 * www/WSGI application directory: %(www_dp)s
 * Temporary directory: %(tmp_dp)s

However, you have more to do. See README.md and doc/deployment.md for details. 
In particular:

 0. You should have read README.md already, and know what I'm talking about.

 1. Make sure that the Python Imaging Library is installed and working. See 
	notes about this in doc/dependencies.md.

 2. Configure the cron job that manages the cache (bin/loris-cache_clean.sh, 
	now at %(cache_clean)s, or bin/loris-http_cache_clean.sh,
	now at %(cache_http_clean)s). Make sure the
	constants match how you have Loris configured, and then set up the cron
	(e.g. `crontab -e -u %(user_n)s`).

 3. Have a look at the WSGI file in %(www_dp)s. It should be fine as-is, but 
	there's always a chance that it isn't. The first thing to try is explictly
	adding the package to your PYTHONPATH (see commented code).

 4. Configure Apache (see doc/apache.md).

You may want to save this message as the path information above is the most 
comprehensive information about what this script just did, what's installed 
where, etc.

Cheers! -Js
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
''' % d

stdout.write(todo)
