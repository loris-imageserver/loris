#!/usr/bin/env python
import os
import shutil
from configobj import ConfigObj


CONFIG_FILE_NAME = 'loris2.conf'
CONFIG_DIR_TARGET_DEFAULT = '/etc/loris2'
WSGI_FILE_NAME = 'loris2.wsgi'


def _data_directory_path():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


def _config_file_path():
    return os.path.join(_data_directory_path(), CONFIG_FILE_NAME)


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
    www_target = config['loris.Loris']['www_dp']
    wsgi_file_path = os.path.join(www_target, WSGI_FILE_NAME)
    with open(wsgi_file_path, 'w') as f:
        f.write(wsgi_content)


def _write_config():
    config_file_target = os.path.join(CONFIG_DIR_TARGET_DEFAULT, CONFIG_FILE_NAME)
    with open(config_file_target, 'wb') as f:
        f.write(_get_default_config_content().encode('utf8'))

def _copy_index_and_favicon(config):
    www_target = config['loris.Loris']['www_dp']
    www_src = os.path.join(_data_directory_path(), 'www')
    index_src = os.path.join(www_src, 'index.txt')
    favicon_src = os.path.join(www_src, 'icons/favicon.ico')
    index_target = os.path.join(www_target, 'index.txt')
    favicon_target_dir = os.path.join(www_target, 'icons')
    favicon_target = os.path.join(favicon_target_dir, 'favicon.ico')
    os.makedirs(favicon_target_dir, exist_ok=True)
    shutil.copyfile(index_src, index_target)
    shutil.copyfile(favicon_src, favicon_target)


def _make_directories(config):
    image_cache = config['img.ImageCache']['cache_dp']
    info_cache = config['img_info.InfoCache']['cache_dp']
    log_dir = config['logging']['log_dir']
    tmp_dir = config['transforms']['jp2']['tmp_dp']
    www_target = config['loris.Loris']['www_dp']
    loris_directories = [
        image_cache,
        info_cache,
        tmp_dir,
        www_target,
        log_dir,
    ]
    for d in loris_directories:
        os.makedirs(d, exist_ok=True)


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

