# setup.py

# To remove:
# rm -r /tmp/loris /etc/loris /var/cache/loris /var/log/loris /var/www/loris
# rm -r /usr/local/bin/loris* /usr/local/lib/python2.7/dist-packages/Loris*.egg

from pwd import getpwnam
from grp import getgrnam
from setuptools import setup
from sys import stderr, stdout
import ConfigParser
import os
import loris
import shutil

VERSION = loris.__version__

# Determine requirements
install_requires = []
try:
	import werkzeug
except ImportError:
	install_requires.append('werkzeug>=0.8.1')

scripts = ['bin/loris-cache_clean.sh']

setup(
	name='Loris',
	version=VERSION,
	packages=['loris'],
	scripts=scripts,
	install_requires=install_requires
)

# other stuff to other places...
this_dir = os.path.abspath(os.path.dirname(__file__))

conf_src = os.path.join(this_dir, 'etc', 'loris.conf')
conf = ConfigParser.RawConfigParser()
conf.read(conf_src)

user = getpwnam(conf.get('run_as', 'name')).pw_uid
group = getgrnam(conf.get('run_as', 'group')).gr_gid

# make empty dirs we need
dir_keys = ('logs', 'cache_root', 'tmp', 'etc')
dirs = dict.fromkeys(dir_keys)
for d in dirs:
	dirs[d] = conf.get('directories', d)
	try:
		if not os.path.exists(dirs[d]):
			os.mkdir(dirs[d], 0755)
			os.chown(dirs[d], user, group)
			stdout.write('Created %s\n' % (dirs[d]))
	except IOError:
		stderr.write('Unable to create directory: ' + dirs[d] + '\n')

# copy config files to /etc/loris:
log_src = os.path.join(this_dir, 'etc', 'logging.conf')
target = dirs['etc']
try:
	for src in (conf_src, log_src):
		dest = os.path.join(target, os.path.basename(src))
		if not os.path.exists(dest):
			stdout.write('Copying %s to %s\n' % (src, target))
			shutil.copy2(src, target)
			os.chown(dest, user, group)
			os.chmod(dest, 0644)

except IOError:
	stderr.write('Unable to copy configuration file to ' + target + '\n')

# copy www files
www_src = os.path.join(this_dir, 'www')
www_target = conf.get('directories', 'www')
try:
	if not os.path.exists(www_target):
		shutil.copytree(www_src, www_target)
		stdout.write('Copied %s to %s\n' % (www_src, www_target))
		os.lchown(www_target, user, group)
		for root, dirs, files in os.walk(www_target):  
			for d in dirs:  
				os.lchown(os.path.join(root, d), user, group)
			for f in files:
				os.lchown(os.path.join(root, f), user, group)

	# make loris.wsgi executable.
	os.chmod(os.path.join(www_target, 'loris.wsgi'), 0744)
except IOError:
	stderr.write('Unable to copy over www directory\n')
