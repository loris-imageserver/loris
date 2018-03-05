#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py
from grp import getgrnam
from pwd import getpwnam
from setuptools import setup
from setuptools.command.install import install
from sys import stderr, stdout, exit
import loris
import os
import shutil
import stat

from pip.download import PipSession
from pip.req import parse_requirements

VERSION = loris.__version__

EX_NOUSER = 67

CONFIG_FILE_NAME = 'loris2.conf'

BIN_DIR_DEFAULT = '/usr/local/bin'
LIB_DIR_DEFAULT = '/usr/local/lib'
CACHE_DIR_DEFAULT = '/var/cache/loris2'

KDU_EXPAND_DEFAULT = os.path.join(BIN_DIR_DEFAULT, 'kdu_expand')
KDU_HELP = 'Path to the Kakadu executable [Default: %s]' % (KDU_EXPAND_DEFAULT,)

LIBKDU_DEFAULT = LIB_DIR_DEFAULT
LIBKDU_HELP = 'Path to THE DIRECTORY THAT CONTAINS libkdu.so [Default: %s]' % (LIBKDU_DEFAULT,)

LOG_DIR_DEFAULT = '/var/log/loris2'
LOG_DIR_HELP = 'Path to directory for logs [Default: %s]' % (LOG_DIR_DEFAULT,)

SOURCE_IMAGE_DIR_DEFAULT = '/usr/local/share/images'
SOURCE_IMAGE_DIR_HELP = 'Path to source images directory [Default: %s]' % (SOURCE_IMAGE_DIR_DEFAULT,)

IMAGE_CACHE_DIR_DEFAULT = '/var/cache/loris2'
IMAGE_CACHE_DIR_HELP = 'Path to image cache directory [Default: %s]' % (IMAGE_CACHE_DIR_DEFAULT,)

INFO_CACHE_DIR_DEFAULT = '/var/cache/loris2'
INFO_CACHE_DIR_HELP = 'Path to info cache directory [Default: %s]' % (INFO_CACHE_DIR_DEFAULT,)

WWW_DIR_DEFAULT = '/var/www/loris2'
WWW_DIR_HELP = 'Path to www directory (wsgi and index file will be here) [Default: %s]' % (WWW_DIR_DEFAULT,)
WSGI_FILE_NAME = 'loris2.wsgi'

TMP_DIR_DEFAULT = '/tmp/loris2'
TMP_DIR_HELP = 'Path to temporary directory (loris will make its temporary files and pipes here) [Default: %s]' % (TMP_DIR_DEFAULT,)

CONFIG_DIR_DEFAULT = '/etc/loris2'
CONFIG_DIR_HELP = 'Where to put the config file. loris2.conf will be here after install. [Default: %s]' % (CONFIG_DIR_DEFAULT,)

USER_DEFAULT = 'loris'
USER_HELP = 'User that will own the application and has permission to write to caches. [Default: %s]' % (USER_DEFAULT,)

GROUP_DEFAULT = 'loris'
GROUP_HELP = 'Group that will own the application and has permission to write to caches. [Default: %s]' % (USER_DEFAULT,)


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


class LorisInstallCommand(install):
    description = 'Installs Loris image server'
    user_options = install.user_options + [
        ('kdu-expand=', None, KDU_HELP),
        ('libkdu=', None, LIBKDU_HELP),
        ('image-cache=', None, IMAGE_CACHE_DIR_HELP),
        ('tmp-dir=', None, TMP_DIR_HELP),
        ('www-dir=', None, WWW_DIR_HELP),
        ('log-dir=', None, LOG_DIR_HELP),
        ('source-images=', None, SOURCE_IMAGE_DIR_HELP),
        ('config-dir=', None, CONFIG_DIR_HELP),
        ('info-cache=', None, INFO_CACHE_DIR_HELP),
        ('loris-owner=', None, USER_HELP),
        ('loris-group=', None, GROUP_HELP),
    ]

    def initialize_options(self):
        self.kdu_expand = KDU_EXPAND_DEFAULT
        self.libkdu = LIBKDU_DEFAULT
        self.source_images = SOURCE_IMAGE_DIR_DEFAULT
        self.image_cache = IMAGE_CACHE_DIR_DEFAULT
        self.info_cache = INFO_CACHE_DIR_DEFAULT
        self.tmp_dir = TMP_DIR_DEFAULT
        self.www_dir = WWW_DIR_DEFAULT
        self.log_dir = LOG_DIR_DEFAULT
        self.config_dir = CONFIG_DIR_DEFAULT
        self.loris_owner = USER_DEFAULT
        self.loris_group = GROUP_DEFAULT
        install.initialize_options(self)

    def finalize_options(self):
        self.__check_user()
        self.loris_owner_id = getpwnam(self.loris_owner).pw_uid
        self.loris_group_id = getgrnam(self.loris_group).gr_gid
        install.finalize_options(self)

    def run(self):
        self.__make_directories()
        self.__write_wsgi()
        self.__copy_index_and_favicon()
        if self.dry_run:
            stdout.write('%sDEBUG INFO%s\n' % ('*'*35,'*'*35))
            stdout.write('kdu-expand: %s\n' % (self.kdu_expand,))
            stdout.write('libkdu: %s\n' % (self.libkdu,))
            stdout.write('image-cache: %s\n' % (self.image_cache,))
            stdout.write('info-cache: %s\n' % (self.info_cache,))
            stdout.write('info-cache: %s\n' % (self.info_cache,))
            stdout.write('tmp-dir: %s\n' % (self.tmp_dir,))
            stdout.write('www-dir: %s\n' % (self.www_dir,))
            stdout.write('log-dir: %s\n' % (self.log_dir,))
            stdout.write('source-images: %s\n' % (self.source_images,))
            stdout.write('config: %s\n' % (self.config_dir,))
            stdout.write('loris-owner: %s\n' % (self.loris_owner,))
            stdout.write('loris-group: %s\n' % (self.loris_group,))
            stdout.write('*'*80+'\n')
        self.do_egg_install()
        self.__update_and_deploy_config()

    def __check_user(self):
        try:
            getpwnam(self.loris_owner).pw_uid
            getgrnam(self.loris_group).gr_gid
        except KeyError:
            msg = '''\nUser "%s" and or group "%s" do(es) not exist.
Please create this user, e.g.:
    `useradd -d /var/www/loris -s /sbin/false %s`\n
''' % (self.loris_owner, self.loris_group, self.loris_owner)
            stderr.write(msg)
            exit(EX_NOUSER)

    def __make_directories(self):
        loris_directories = [
            self.image_cache,
            self.info_cache,
            self.tmp_dir,
            self.www_dir,
            self.log_dir,
            self.config_dir
        ]
        map(self.__init_dir, loris_directories)

    def __init_dir(self, d):
        # Could do something here to warn if dir exists but permissions or
        # ownership aren't sufficient.
        if not os.path.exists(d):
            os.makedirs(d)
            stdout.write('Created %s\n' % (d,))
            os.chown(d, self.loris_owner_id, self.loris_group_id)
            stdout.write('Changed ownership of %s to %s:%s\n' %
                (d,self.loris_owner,self.loris_group))

        s = os.stat(d)
        permissions = oct(stat.S_IMODE(s.st_mode))
        if permissions != oct(0o755):
            os.chmod(d, 0o755)
            stdout.write('Set permissions for %s to 0755\n' % (d,))

    def __write_wsgi(self):
        config_file_path = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        wsgi_file_path = os.path.join(self.www_dir, WSGI_FILE_NAME)
        content = '''#!/usr/bin/env python
from loris.webapp import create_app
# Uncomment and configure below if you are using virtualenv
# import site
# site.addsitedir('/path/to/my/virtualenv/lib/python2.x/site-packages')
application = create_app(config_file_path='%s')
''' % (config_file_path,)
        with open(wsgi_file_path, 'w') as f:
            f.write(content)
        os.chmod(wsgi_file_path, 0o755)
        os.chown(wsgi_file_path, self.loris_owner_id, self.loris_group_id)
    @property
    def __here(self):
        return os.path.dirname(os.path.realpath(__file__))

    def __copy_index_and_favicon(self):
        www_src = os.path.join(self.__here, 'www')
        index_src = os.path.join(www_src, 'index.txt')
        favicon_src = os.path.join(www_src, 'icons/favicon.ico')
        index_target = os.path.join(self.www_dir, 'index.txt')
        favicon_target_dir = os.path.join(self.www_dir, 'icons')
        favicon_target = os.path.join(favicon_target_dir, 'favicon.ico')
        self.__init_dir(favicon_target_dir)
        shutil.copyfile(index_src, index_target)
        shutil.copyfile(favicon_src, favicon_target)
        for f in (index_target, favicon_target):
            os.chmod(f, 0o644)
            os.chown(f, self.loris_owner_id, self.loris_group_id)

    def __update_and_deploy_config(self):
        from configobj import ConfigObj # can do now that we've installed it!
        config_file_src = os.path.join(self.__here, 'etc', CONFIG_FILE_NAME)
        config_file_target = os.path.join(self.config_dir, CONFIG_FILE_NAME)

        config = ConfigObj(config_file_src, unrepr=True, interpolation=False)

        config['loris.Loris']['tmp_dp'] = self.tmp_dir
        config['loris.Loris']['www_dp'] = self.www_dir
        config['loris.Loris']['run_as_user'] = self.loris_owner
        config['loris.Loris']['run_as_group'] = self.loris_group
        config['logging']['log_dir'] = self.log_dir
        config['resolver']['src_img_root'] = self.source_images
        config['img.ImageCache']['cache_dp'] = self.image_cache
        config['img_info.InfoCache']['cache_dp'] = self.info_cache
        config['transforms']['jp2']['kdu_expand'] = self.kdu_expand
        config['transforms']['jp2']['kdu_libs'] = self.libkdu
        config['transforms']['jp2']['tmp_dp'] = self.tmp_dir

        config.filename = config_file_target
        config.write()


install_requires = parse_requirements(
    local_file('requirements.txt'), session=PipSession()
)


def _read(fname):
    return open(local_file(fname)).read()


setup(
    cmdclass={ 'install' : LorisInstallCommand },
    name='Loris',
    author='Jon Stroop',
    author_email='jpstroop@gmail.com',
    url='https://github.com/loris-imageserver/loris',
    description = ('IIIF Image API 2.0 Level 2 compliant Image Server'),
    long_description=_read('README.md'),
    license='Simplified BSD',
    version=VERSION,
    packages=['loris'],
    install_requires=[str(ir.req) for ir in install_requires]
)


## TODO: write this only if we succeeded! include info about cron, etc.

# todo = '''
# *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# Installation was successful. Here's where things are:

#  * Loris configuration: %(config)s
#  * Cache cleaner Simple cron: %(cache_clean)s
#  * Cache cleaner HTTP cron: %(cache_http_clean)s
#  * JP2 executable: %(jptoo_exe)s (kdu_expand or opj_decompress)
#  * JP2 libraries: %(jptoo_lib)s (libkdu or libopenjp2)
#  * Logs: %(logs)s
#  * Image cache: %(cache_dp)s
#  * Info cache: %(info_cache_dp)s
#  * www/WSGI application directory: %(www_dp)s
#  * Temporary directory: %(tmp_dp)s

# However, you have more to do. See README.md and doc/deployment.md for details.
# In particular:

#  0. You should have read README.md already, and know what I'm talking about.

#  1. Make sure that the Python Imaging Library is installed and working. See
#   notes about this in doc/dependencies.md.

#  2. Configure the cron job that manages the cache (bin/loris-cache_clean.sh,
#   now at %(cache_clean)s, or bin/loris-http_cache_clean.sh,
#   now at %(cache_http_clean)s). Make sure the
#   constants match how you have Loris configured, and then set up the cron
#   (e.g. `crontab -e -u %(user_n)s`).

#  3. Have a look at the WSGI file in %(www_dp)s. It should be fine as-is, but
#   there's always a chance that it isn't. The first thing to try is explicitly
#   adding the package to your PYTHONPATH (see commented code).

#  4. Configure Apache (see doc/apache.md).

# You may want to save this message as the path information above is the most
# comprehensive information about what this script just did, what's installed
# where, etc.

# Cheers! -Js
# *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# ''' % d

# stdout.write(todo)
