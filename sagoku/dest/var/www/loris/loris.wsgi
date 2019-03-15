#!/usr/bin/env python
import os
from loris.webapp import create_app

sgk_env = os.environ.get('SGK_ENVIRONMENT', 'test')
application = create_app(config_file_path='/etc/loris/%s.conf' % sgk_env)