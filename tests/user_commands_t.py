#-*- coding: utf-8 -*-

from __future__ import absolute_import
import os
import shutil
import tempfile
import unittest
from configobj import ConfigObj
from loris import user_commands


class TestCreateFilesAndDirectories(unittest.TestCase):

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_1(self):
        config = ConfigObj(user_commands._config_file_path(), unrepr=True, interpolation=False)
        #replace with TemporaryDirectory() when we can drop python 2
        self.working_dir = tempfile.mkdtemp()
        image_cache = os.path.join(self.working_dir, 'image_cache')
        info_cache = os.path.join(self.working_dir, 'info_cache')
        log_dir = os.path.join(self.working_dir, 'logs')
        www_dir = os.path.join(self.working_dir, 'www')
        config['img.ImageCache']['cache_dp'] = image_cache
        config['img_info.InfoCache']['cache_dp'] = info_cache
        config['logging']['log_dir'] = log_dir
        config['loris.Loris']['www_dp'] = www_dir
        user_commands.create_default_files_and_directories(config)
        for d in [image_cache, info_cache, log_dir, www_dir]:
            self.assertTrue(os.path.exists(d))

