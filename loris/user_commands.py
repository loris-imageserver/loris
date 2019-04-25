#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
from configobj import ConfigObj


CONFIG_FILE_NAME = 'loris2.conf'
CONFIG_DIR_DEFAULT = '/etc/loris2'
WSGI_FILE_NAME = 'loris2.wsgi'


def _src_code_repo_root():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _init_dir(d):
    # Could do something here to warn if dir exists but permissions or
    # ownership aren't sufficient.
    if not os.path.exists(d):
        os.makedirs(d)


def _config_file_path():
    return os.path.join(_src_code_repo_root(), 'etc', CONFIG_FILE_NAME)


def _get_default_config_content():
    with open(_config_file_path(), 'rb') as f:
        return f.read().decode('utf8')


def _get_default_wsgi():
    content = '''#!/usr/bin/env python
from loris.webapp import create_app
# Uncomment and configure below if you are using virtualenv
# import site
# site.addsitedir('/path/to/my/virtualenv/lib/python2.x/site-packages')
application = create_app(config_file_path='%s')
''' % (_config_file_path(),)
    return content


def _write_wsgi(config):
    wsgi_content = _get_default_wsgi()
    www_dir = config['loris.Loris']['www_dp']
    wsgi_file_path = os.path.join(www_dir, WSGI_FILE_NAME)
    with open(wsgi_file_path, 'w') as f:
        f.write(wsgi_content)


def _write_config():
    config_file_target = os.path.join(CONFIG_DIR_DEFAULT, CONFIG_FILE_NAME)
    with open(config_file_target, 'wb') as f:
        f.write(_get_default_config_content().encode('utf8'))

def _copy_index_and_favicon(config):
    www_dir = config['loris.Loris']['www_dp']
    www_src = os.path.join(_src_code_repo_root(), 'www')
    index_src = os.path.join(www_src, 'index.txt')
    favicon_src = os.path.join(www_src, 'icons/favicon.ico')
    index_target = os.path.join(www_dir, 'index.txt')
    favicon_target_dir = os.path.join(www_dir, 'icons')
    favicon_target = os.path.join(favicon_target_dir, 'favicon.ico')
    _init_dir(favicon_target_dir)
    shutil.copyfile(index_src, index_target)
    shutil.copyfile(favicon_src, favicon_target)


def _make_directories(config):
    image_cache = config['img.ImageCache']['cache_dp']
    info_cache = config['img_info.InfoCache']['cache_dp']
    log_dir = config['logging']['log_dir']
    tmp_dir = config['transforms']['jp2']['tmp_dp']
    www_dir = config['loris.Loris']['www_dp']
    loris_directories = [
        image_cache,
        info_cache,
        tmp_dir,
        www_dir,
        log_dir,
    ]
    for d in loris_directories:
        _init_dir(d)


def display_default_config_file():
    print(_get_default_config_content())


def display_default_wsgi_file():
    wsgi_content = _get_default_wsgi()
    print(wsgi_content)


def create_default_files_and_directories(config=None):
    if not config:
        config = ConfigObj(_config_file_path(), unrepr=True, interpolation=False)
    _make_directories(config)
    _write_wsgi(config)
    _copy_index_and_favicon(config)

