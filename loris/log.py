# log.py
#-*-coding:utf-8-*-

from ConfigParser import RawConfigParser
import logging
import logging.handlers
import os
import sys

# Loris's etc dir MUST either be a sibling to the loris/loris directory or at 
# the below:
prod_conf_fp = os.path.join('/etc', 'loris', 'loris.conf')

config = RawConfigParser()
if os.path.exists(prod_conf_fp):
	config.read(prod_conf_fp)
else:
	project_dp = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
	dev_conf_fp = os.path.join(project_dp, 'etc', 'loris.conf')
	config.read(dev_conf_fp)

LOG_FMT = '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s'

# Set LOG_LEVEL to logging.INFO or higher in production.
conf_level = config.get('log', 'log_level')
LOG_LEVEL = None
if conf_level == 'CRITICAL': LOG_LEVEL = logging.CRITICAL
elif conf_level == 'ERROR':	LOG_LEVEL = logging.ERROR
elif conf_level == 'WARNING': LOG_LEVEL = logging.WARNING
elif conf_level == 'INFO': LOG_LEVEL = logging.INFO
else: LOG_LEVEL = logging.DEBUG

if config.get('log', 'log_to') == 'file':
	LOG_DIR = config.get('log', 'log_dir')
	MAX_LOG_SIZE = config.getint('log', 'max_size')
	MAX_BACKUPS = config.getint('log', 'max_backups')

	try:
		if not os.path.exists(LOG_DIR):
			os.makedirs(LOG_DIR)
	except OSError as ose: 
		sys.stderr.write('%s (%s)\n' % (os.strerror(ose.errno),ose.filename))
		sys.stderr.write('Exiting')
		sys.exit(77)

	if not os.access(LOG_DIR, os.W_OK):
		sys.stderr.write('%s is not writable\n' % (LOG_DIR,))
		sys.stderr.write('Exiting')
		sys.exit(77)

def get_logger(name):
	logger = logging.getLogger(name)
	logger.setLevel(LOG_LEVEL)

	formatter = logging.Formatter(fmt=LOG_FMT)

	if config.get('log', 'log_to') == 'file':
		fp = '%s.log' % (os.path.join(LOG_DIR, name),)
		handler = logging.handlers.RotatingFileHandler(fp,
			maxBytes=MAX_LOG_SIZE, 
			backupCount=MAX_BACKUPS,
			delay=True)
		handler.setFormatter(formatter)
		logger.addHandler(handler)
	else:
		# STDERR
		err_handler = logging.StreamHandler(sys.__stderr__)
		err_handler.addFilter(StdErrFilter())
		err_handler.setFormatter(formatter)
		logger.addHandler(err_handler)
		
		# STDOUT
		out_handler = logging.StreamHandler(sys.__stdout__)
		out_handler.addFilter(StdOutFilter())
		out_handler.setFormatter(formatter)
		logger.addHandler(out_handler)

	return logger

class StdErrFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno >= 30 else 0

class StdOutFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno <= 20 else 0
