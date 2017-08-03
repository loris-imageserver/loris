# -*- encoding: utf-8 -*-

import pytest

from loris.loris_exception import ConfigError
from loris.webapp import configure_logging


class TestLoggingConfig(object):

    @pytest.mark.parametrize('log_to', ['notafile', '', 'disk'])
    def test_bad_log_to_is_configerror(self, log_to):
        with pytest.raises(ConfigError):
            configure_logging(config={'log_to': log_to})

    @pytest.mark.parametrize('missing_key', ['log_to', 'log_level', 'format'])
    def test_missing_mandatory_key_is_error(self, missing_key):
        config = {
            'log_to': 'console',
            'log_level': 'INFO',
            'format': '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
        }
        del config[missing_key]
        with pytest.raises(ConfigError):
            configure_logging(config=config)
