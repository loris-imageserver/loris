#!/usr/bin/env python
#-*- coding: utf-8 -*-

from base64 import urlsafe_b64encode
import logging
import logging.config
import os
import random
import struct
import subprocess
import ConfigParser

# Private Static Constants 
_BMP = ".bmp"
_JPG = ".jpg"
_JP2 = ".jp2"
_LIB = os.getcwd() + "/lib"
_BIN = os.getcwd() + "/bin"
_ETC = os.getcwd() + "/etc"
_ENV = {"LD_LIBRARY_PATH":_LIB, "PATH":_LIB + ":$PATH"}

# For shellouts:
KDU_EXPAND = _BIN + "/kdu_expand -num_threads 4 -quiet"

def setup():
	global TMP_DIR
	global CACHE_ROOT
	global SRC_IMAGES_ROOT
	global CJPEG
	global MKFIFO
	global RM
	global logr

	# Logging
	logging.config.fileConfig(_ETC + '/logging.conf')
	logr = logging.getLogger('main')
	
	# Main configuration
	conf = ConfigParser.RawConfigParser()
	conf.read(_ETC + '/main.conf')
	
	TMP_DIR = conf.get('directories', 'tmp')
	CACHE_ROOT = conf.get('directories', 'cache_root')
	SRC_IMAGES_ROOT = conf.get('directories', 'src_img_root')
	for d in (TMP_DIR, CACHE_ROOT):
		if not os.path.exists(d):
			os.makedirs(d, 0755)
			logr.info("Created " + d)
			
	# TODO: raise if SRC_IMAGES_ROOT is not a dir, does not exist, or is not readable 
	
	CJPEG = conf.get('utilities', 'cjpeg')
	MKFIFO = conf.get('utilities', 'mkfifo')
	RM = conf.get('utilities', 'rm')


def rand_str():
	"""
	based on http://stackoverflow.com/questions/785058/random-strings-in-python-2-6-is-this-ok
	"""
	length = 4
	nbits = length * 6 + 1
	bits = random.getrandbits(nbits)
	uc = u"%0x" % bits
	newlen = int(len(uc) / 2) * 2 # we have to make the string an even length
	ba = bytearray.fromhex(uc[:newlen])
	return urlsafe_b64encode(str(ba))[:length]

def get_jp2_data(path):
	"""
	Get the dimenstions of a JP2.
	@return: (width, height)
	"""
	jp2 = open(path, 'rb')
	jp2.read(2)
	b = jp2.read(1)
	
	while (ord(b) != 0xFF):	b = jp2.read(1)
	b = jp2.read(1) #skip over the SOC, 0x4F 
	
	while (ord(b) != 0xFF):	b = jp2.read(1)
	b = jp2.read(1) # 0x51: The SIZ marker segment
	if (ord(b) == 0x51):
	
		jp2.read(4) # get through Lsiz, Rsiz (16 bits each)
	
		# Xsiz
		width = int(struct.unpack(">HH", jp2.read(4))[1])
		# Ysiz
		height = int(struct.unpack(">HH", jp2.read(4))[1])
	
	jp2.close()
	logr.debug(path + " dims: w: " + str(width) + " h: " + str(height))
	return (width, height)	

def get_jpeg_dimensions(path):
	"""
	Get the dimensions of a JPEG
	@return: (width, height)
	"""
	jpeg = open(path, 'rb')
	jpeg.read(2)
	b = jpeg.read(1)
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
	
	jpeg.close()
	logr.debug(path + " dims: w: " + str(width) + " h: " + str(height))
	return (width, height)

# Do we want: http://docs.python.org/library/queue.html ?
def expand(id, region='full', size='full', rotation=0, quality='native', format='.jpg'):
	"""
	@return the path to the new image.
	"""
	jp2 = resolve_identifier(id)
	rotation = str(90 * int(rotation / 90)) # round to closest factor of 90
	
	out_dir = os.path.join(CACHE_ROOT, id, region, size, rotation)
	out = os.path.join(out_dir, quality) + format  
	
	# Use a named pipe to give kdu and cjpeg format info.
	fifopath = os.path.join(TMP_DIR, rand_str() + _BMP)
	mkfifo_cmd = MKFIFO + " " + fifopath
	logr.debug(mkfifo_cmd) 
	mkfifo_proc = subprocess.Popen(mkfifo_cmd, shell=True)
	mkfifo_proc.wait()
	
	# Build the kdu_expand call
	kdu_cmd = KDU_EXPAND + " -i " + jp2 
	if region != 'full': kdu_cmd = kdu_cmd + " -region " + region
	if rotation != 0:  kdu_cmd = kdu_cmd + " -rotate " + rotation
	kdu_cmd = kdu_cmd + " -o " + fifopath
	logr.debug(kdu_cmd)
	kdu_proc = subprocess.Popen(kdu_cmd, env=_ENV, shell=True)

	# What are the implications of not being able to wait here (not sure why
	# we can't, but it hangs when we try). I *think* that as long as there's 
	# data flowing into the pipe when the next process (below) starts we're 
	# just fine.
	
	# TODO: if format is not jpg, [do something] (see spec)
	# TODO: quality, probably in the recipe below
	
	if not os.path.exists(out_dir):
		os.makedirs(out_dir, 0755)
		logr.info("Made directory: " + out_dir)
	cjpeg_cmd = CJPEG + " -outfile " + out + " " + fifopath 
	logr.debug(cjpeg_cmd)
	cjpeg_proc = subprocess.call(cjpeg_cmd, shell=True)
	logr.info("Made file: " + out)

	rm_cmd = RM + " " + fifopath
	logr.debug(rm_cmd)
	rm_proc = subprocess.Popen(rm_cmd, shell=True)
	
	return out

def check_cache():
	pass


def resolve_identifier(ident):
	"""
	Given the identifier of an image, resolve it to an actual path. This would 
	probably need to be overridden to suit different environments.
	
	This simple version just prepends a constant path to the identfier supplied,
	and appends a file extension, resulting in an absolute path on the filesystem
	"""
	return os.path.join(SRC_IMAGES_ROOT, ident + _JP2)


if __name__ == "__main__":
	# Making the jpeg is over 4x faster when reading from the local file system.
	# Change the config file to prove it.
	
	setup()
	id = "pudl0001/4609321/s42/00000004"
	jp2 = resolve_identifier(id)
#	get_jp2_data(jp2)
	# check the cache for a match
	# if its there, return it
	# else, parse the path and call expand()
	expand(id, rotation=90)
# TODO: make expand handle iiif syntax for regions, parse that to look like below:
#	expand(id, region="\{0.3,0.2\},\{0.6,0.4\}") 
	#print get_jpeg_dimensions("/home/jstroop/workspace/patokah/data/deriv_images/00000009.jpg")
