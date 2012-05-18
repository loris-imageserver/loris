#!/usr/bin/env python
#-*- coding: utf-8 -*-

from base64 import urlsafe_b64encode
import StringIO
import logging
import logging.config
import os
import random
import struct
import subprocess

# Directories. TODO: At least some of this should be in a config file. We'll
# also need to check permissions; maybe be able to create, etc.
#LOG_DIR = "log/"

TMP_DIR = "/tmp/patokah" # this is just going to hold FIFOs
DERIV_IMAGES_DIR = "/data/deriv_images"
SRC_IMAGES_DIR = "/data/src_images"

# Utility dependencies. TODO: probably in a config as well.
#CJPEG = "/usr/bin/libjpeg-progs-divert/cjpeg -quality 95"
CJPEG = "/usr/bin/cjpeg -quality 95" # can we make this faster
MKFIFO = "/usr/bin/mkfifo"
RM = "/bin/rm"

# Private Static Constants 
_BMP = ".bmp"
_JPG = ".jpg"
_LIB = os.getcwd() + "/lib"
_BIN = os.getcwd() + "/bin"
_ETC = os.getcwd() + "/etc"
_LOGGING_CONF = _ETC + "/logging.conf"
_ENV = {"LD_LIBRARY_PATH":_LIB, "PATH":_LIB + ":$PATH"}

# For shellouts:
KDU_EXPAND = _BIN + "/kdu_expand -num_threads 4 -quiet" # we could consider -record if things get too complex

# Logging
logging.config.fileConfig(_LOGGING_CONF)
logr = logging.getLogger('main')

def rand_str(length):
	"""
	From: http://stackoverflow.com/questions/785058/random-strings-in-python-2-6-is-this-ok
	"""
	nbits = length * 6 + 1
	random.randint
	bits = random.getrandbits(nbits)
	uc = u"%0x" % bits
	newlen = int(len(uc) / 2) * 2 # we have to make the string an even length
	ba = bytearray.fromhex(uc[:newlen])
	return urlsafe_b64encode(str(ba))[:length]

def get_jpeg_dimensions(path):
	"""
	Based on 
	<a href="http://www.opensource.org/licenses/bsd-license.php">New BSD License</a>
	"""
	height = -1
	width = -1
	f = open(path, 'r')
	jpeg = StringIO.StringIO(f.read(512))
	f.close()
	jpeg.read(2)
	b = jpeg.read(1)
	try:
		while (b and ord(b) != 0xDA):
			while (ord(b) != 0xFF): b = jpeg.read(1)
			while (ord(b) == 0xFF): b = jpeg.read(1)
			
			if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
				jpeg.read(3)
				h, w = struct.unpack(">HH", jpeg.read(4))
				break
			else:
				jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0]) - 2)
				
			b = jpeg.read(1)
		width = int(w)
		height = int(h)
	except struct.error:
		pass
	except ValueError:
		pass
	logr.debug(path + " w: " + str(width) + " h: " + str(height))
	return (width, height)

# Do we want: http://docs.python.org/library/queue.html ?
def expand(jp2, out=False, region=False, rotation=False, level=False):
	# Use a named pipe to give kdu and cjpeg format info.
	
	fifopath = os.path.join(TMP_DIR, rand_str(4) + _BMP)
	mkfifo_cmd = MKFIFO + " " + fifopath
	logr.debug(mkfifo_cmd) 
	mkfifo_proc = subprocess.Popen(mkfifo_cmd, shell=True)
	mkfifo_proc.wait()
	
	# Build the kdu_expand call
	kdu_cmd = KDU_EXPAND + " -i " + jp2 
	if level: kdu_cmd = kdu_cmd + " -reduce " + level
	if region: kdu_cmd = kdu_cmd + " -region " + region
	if rotation:  kdu_cmd = kdu_cmd + " -rotate " + str(90 * int(rotation / 90)) # round to closest factor of 90
	kdu_cmd = kdu_cmd + " -o " + fifopath
	logr.debug(kdu_cmd)
	kdu_proc = subprocess.Popen(kdu_cmd, env=_ENV, shell=True)

	# What are the implications of not being able to wait here (not sure why
	# we can't, but it hangs when we try). I *think* that as long as there's 
	# data flowing into the pipe when the next process (below) starts we're 
	# just fine.
	
	cjpeg_cmd = CJPEG
	if out: 
		cjpeg_cmd = cjpeg_cmd + " -outfile " + out
	cjpeg_cmd = cjpeg_cmd + " " + fifopath
	logr.debug(cjpeg_cmd)
	cjpeg_proc = subprocess.call(cjpeg_cmd, shell=True)

	rm_cmd = RM + " " + fifopath
	logr.debug(rm_cmd)
	rm_proc = subprocess.Popen(rm_cmd, shell=True)

def setup():
	if not os.path.exists(TMP_DIR):
		os.mkdir(TMP_DIR)
	logr.info("Created " + TMP_DIR)

if __name__ == "__main__":
	setup()
	jp2 = "/home/jstroop/workspace/patokah/data/src_images/00000009.jp2"

	outPath = os.path.splitext(jp2.replace(SRC_IMAGES_DIR, DERIV_IMAGES_DIR))[0] + _JPG 
#	expand(jp2, outPath, rotation=44)
#	expand(jp2, "outPath", region="\{0.3,0.2\},\{0.6,0.4\}")
	print get_jpeg_dimensions("/home/jstroop/workspace/patokah/data/deriv_images/00000009.jpg")
