# -*- encoding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler

from loris.loris_exception import ConfigError


class StdErrFilter(logging.Filter):
    """Logging filter for stderr."""
    def filter(self, record):
        return 1 if record.levelno >= 30 else 0


class StdOutFilter(logging.Filter):
    """Logging filter for stdout."""
    def filter(self, record):
        return 1 if record.levelno <= 20 else 0


def _validate_logging_config(config):
    """
    Validate the logging config before setting up a logger.
    """
    mandatory_keys = ['log_to', 'log_level', 'format']
    missing_keys = []
    for key in mandatory_keys:
        if key not in config:
            missing_keys.append(key)

    if missing_keys:
        raise ConfigError(
            'Missing mandatory logging parameters: %r' %
            ','.join(missing_keys)
        )

    if config['log_to'] not in ('file', 'console'):
        raise ConfigError(
            'logging.log_to=%r, expected one of file/console' % config['log_to']
        )

    if config['log_to'] == 'file':
        mandatory_keys = ['log_dir', 'max_size', 'max_backups']
        missing_keys = []
        for key in mandatory_keys:
            if key not in config:
                missing_keys.append(key)

        if missing_keys:
            raise ConfigError(
                'When log_to=file, the following parameters are required: %r' %
                ','.join(missing_keys)
            )


def configure_logging(config):
    _validate_logging_config(config)

    logger = logging.getLogger()

    try:
        logger.setLevel(config['log_level'])
    except ValueError:
        logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt=config['format'])

    if not getattr(logger, 'handler_set', None):
        if config['log_to'] == 'file':
            fp = '%s.log' % (path.join(config['log_dir'], 'loris'),)
            handler = RotatingFileHandler(fp,
                maxBytes=config['max_size'],
                backupCount=config['max_backups'],
                delay=True)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        else:
            from sys import __stderr__, __stdout__
            # STDERR
            err_handler = logging.StreamHandler(__stderr__)
            err_handler.addFilter(StdErrFilter())
            err_handler.setFormatter(formatter)
            logger.addHandler(err_handler)

            # STDOUT
            out_handler = logging.StreamHandler(__stdout__)
            out_handler.addFilter(StdOutFilter())
            out_handler.setFormatter(formatter)
            logger.addHandler(out_handler)

            logger.handler_set = True
    return logger
