# -*- encoding: utf-8 -*-

import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

import pytest

from loris.loris_exception import ConfigError
from loris.webapp import configure_logging


valid_console_config = {
    'log_to': 'console',
    'log_level': 'INFO',
    'format': '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
}

valid_file_config = {
    'log_to': 'file',
    'log_level': 'INFO',
    'format': '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
    'log_dir': '/var/log/loris',
    'max_size': 100000,
    'max_backups': 5,
}


class TestLoggingConfig(object):

    @pytest.mark.parametrize('log_to', ['notafile', '', 'disk'])
    def test_bad_log_to_is_configerror(self, log_to):
        config = {
            'log_to': log_to,
            'log_level': 'INFO',
            'format': '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
        }
        with pytest.raises(ConfigError) as err:
            configure_logging(config=config)
        assert 'expected one of file/console' in str(err.value)

    @pytest.mark.parametrize('key', ['log_to', 'log_level', 'format'])
    def test_missing_mandatory_key_is_error(self, key):
        config = {k: v for k, v in valid_console_config.items() if k != key}
        with pytest.raises(ConfigError) as err:
            configure_logging(config=config)
        assert 'Missing mandatory logging parameters' in str(err.value)

    @pytest.mark.parametrize('key', ['log_dir', 'max_size', 'max_backups'])
    def test_missing_mandatory_key_with_log_to_file_is_error(self, key):
        config = {k: v for k, v in valid_file_config.items() if k != key}
        with pytest.raises(ConfigError) as err:
            configure_logging(config=config)
        assert 'When log_to=file, the following parameters are required' in str(err.value)

    @pytest.mark.parametrize('log_config, expected_level', [
        ('CRITICAL', logging.CRITICAL),
        ('ERROR', logging.ERROR),
        ('WARNING', logging.WARNING),
        ('INFO', logging.INFO),
        ('DEBUG', logging.DEBUG),
        ('debug', logging.DEBUG),
        ('slow loris', logging.DEBUG),
    ])
    def test_log_level_is_configured_correctly(self, log_config, expected_level, reset_logger):
        config = {
            'log_to': 'console',
            'log_level': log_config,
            'format': '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
        }
        logger = configure_logging(config=config)
        assert logger.level == expected_level

    def test_valid_console_config_is_okay(self, reset_logger):
        logger = configure_logging(config=valid_console_config)

        assert len(logger.handlers) == 2
        assert all(isinstance(h, StreamHandler) for h in logger.handlers)
        assert logger.handler_set

    def test_valid_file_config_is_okay(self, reset_logger):
        logger = configure_logging(config=valid_file_config)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], RotatingFileHandler)
        assert logger.handler_set

    @pytest.mark.parametrize('config', [
        valid_console_config, valid_file_config
    ])
    def test_logging_config_is_idempotent(self, config, reset_logger):
        """
        If we call ``configure_logging()`` more than once, we don't get
        extra handlers or filters created.
        """
        logger = configure_logging(config=config)
        handler_count = len(logger.handlers)
        filter_count = len(logger.filters)

        configure_logging(config=config)
        assert len(logger.handlers) == handler_count
        assert len(logger.filters) == filter_count
