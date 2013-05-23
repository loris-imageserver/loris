# log_config.py
# __init__.py
#-*-coding:utf-8-*-

import ConfigParser
import logging
import logging.handlers
import os
import sys

# config = ConfigParser.ConfigParser()
# conf_fp = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../conf.ini')
# config.read(os.path.join(conf_fp))

# LOG_DIR = config.get('logs', 'log_dir')
# INCLUDE_DEBUG = config.getboolean('logs', 'include_debug')
# STDERR = config.getboolean('logs', 'stderr')
# STDOUT = config.getboolean('logs', 'stdout')

# MAX_OUT_LOG_SIZE = 5242880 # 5 MB
# MAX_OUT_LOG_BACKUPS = 10

# MAX_ERR_LOG_SIZE = 5242880 # 5 MB
# MAX_ERR_LOG_BACKUPS = 10

LOG_FMT = '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s'


# try:
# 	if not os.path.exists(LOG_DIR):
# 		os.makedirs(LOG_DIR)

# except Exception as e:
# 	sys.stderr.write('%s\n' % (str(e),))
# 	sys.exit(1)


class StdErrFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno >= 30 else 0

class StdOutFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno <= 20 else 0
		# if INCLUDE_DEBUG:
		# 	return 1 if record.levelno <= 20 else 0
		# else:
		# 	return 1 if record.levelno <= 20 and record.levelno > 10 else 0 

def get_logger(name):
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)

	formatter = logging.Formatter(fmt=LOG_FMT)

	# for printing to stderr
	# if STDERR:
	err_handler = logging.StreamHandler(sys.__stderr__)
	err_handler.addFilter(StdErrFilter())
	err_handler.setFormatter(formatter)
	logger.addHandler(err_handler)
	
	# # stderr to a file
	# err_fp = '%s.err' % (os.path.join(LOG_DIR, name),)
	# rferr_handler = logging.handlers.RotatingFileHandler(err_fp,
	# 	maxBytes=MAX_ERR_LOG_SIZE, 
	# 	backupCount=MAX_ERR_LOG_BACKUPS)
	# rferr_handler.addFilter(StdErrFilter())
	# rferr_handler.setFormatter(formatter)
	# logger.addHandler(rferr_handler)

	# For printing to stdout
	# if STDOUT:
	out_handler = logging.StreamHandler(sys.__stdout__)
	out_handler.addFilter(StdOutFilter())
	out_handler.setFormatter(formatter)
	logger.addHandler(out_handler)

	# # stdout to a file
	# out_fp = '%s.out' % (os.path.join(LOG_DIR, name),)
	# rfout_handler = logging.handlers.RotatingFileHandler(out_fp,
	# 	maxBytes=MAX_OUT_LOG_SIZE, 
	# 	backupCount=MAX_OUT_LOG_BACKUPS)
	# rfout_handler.addFilter(StdOutFilter())
	# rfout_handler.setFormatter(formatter)
	# logger.addHandler(rfout_handler)

	return logger