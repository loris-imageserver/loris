# log_config.py
#-*-coding:utf-8-*-

import ConfigParser
import logging
import logging.handlers
import os
import sys

LOG_FMT = '%(asctime)s (%(name)s) [%(levelname)s]: %(message)s'

# Set LOG_LEVEL to logging.INFO or higher in production.
LOG_LEVEL = logging.DEBUG 

# # Comment in the below, and two blocks in get_logger, to log to files
# # Note that the LOG_DIR must be writable by the application owner.
# # You'll probably want to comment out the stderr/stdout handlers as well.

LOG_DIR = '/var/log/loris' # if you change this, change it in setup.py too!
# MAX_OUT_LOG_SIZE = 5242880 # 5 MB
# MAX_OUT_LOG_BACKUPS = 10
# MAX_ERR_LOG_SIZE = 5242880 # 5 MB
# MAX_ERR_LOG_BACKUPS = 10

# try:
# 	if not os.path.exists(LOG_DIR):
# 		os.makedirs(LOG_DIR)
# except OSError as ose: 
# 	sys.stderr.write('%s (%s)\n' % (os.strerror(ose.errno),ose.filename))
# 	sys.stderr.write('Exiting')
# 	sys.exit(77)

# if not os.access(LOG_DIR, os.W_OK):
# 	sys.stderr.write('%s is not writable\n' % (LOG_DIR,))
# 	sys.stderr.write('Exiting')
# 	sys.exit(77)

def get_logger(name):
	logger = logging.getLogger(name)
	logger.setLevel(LOG_LEVEL)

	formatter = logging.Formatter(fmt=LOG_FMT)

	# FOR PRINTING TO STDERR
	err_handler = logging.StreamHandler(sys.__stderr__)
	err_handler.addFilter(StdErrFilter())
	err_handler.setFormatter(formatter)
	logger.addHandler(err_handler)
	
	# FOR PRINTING TO STDOUT
	out_handler = logging.StreamHandler(sys.__stdout__)
	out_handler.addFilter(StdOutFilter())
	out_handler.setFormatter(formatter)
	logger.addHandler(out_handler)

	# # STDERR TO A FILE
	# err_fp = '%s.err' % (os.path.join(LOG_DIR, name),)
	# rferr_handler = logging.handlers.RotatingFileHandler(err_fp,
	# 	maxBytes=MAX_ERR_LOG_SIZE, 
	# 	backupCount=MAX_ERR_LOG_BACKUPS)
	# rferr_handler.addFilter(StdErrFilter())
	# rferr_handler.setFormatter(formatter)
	# logger.addHandler(rferr_handler)

	# # STDOUT TO A FILE
	# out_fp = '%s.out' % (os.path.join(LOG_DIR, name),)
	# rfout_handler = logging.handlers.RotatingFileHandler(out_fp,
	# 	maxBytes=MAX_OUT_LOG_SIZE, 
	# 	backupCount=MAX_OUT_LOG_BACKUPS)
	# rfout_handler.addFilter(StdOutFilter())
	# rfout_handler.setFormatter(formatter)
	# logger.addHandler(rfout_handler)

	return logger

class StdErrFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno >= 30 else 0

class StdOutFilter(logging.Filter):
	def filter(self,record):
		return 1 if record.levelno <= 20 else 0
