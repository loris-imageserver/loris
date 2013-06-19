# transformers.py
# -*- coding: utf-8 -*-

from PIL import Image
from PIL.ImageOps import grayscale
from PIL.ImageFile import Parser
from log_config import get_logger
from loris_exception import LorisException
from os import makedirs, path, unlink
import random
import string
import subprocess

logger = get_logger(__name__)

def round_rotation(rotation):
	'''Round the roation to the nearest 90. 
	Args:
		rotation (str)
	'''
	return str(int(90 * round(float(rotation) / 90)))

def make_tmp_fp(tmp, fmt):
	n = ''.join(random.choice(string.ascii_lowercase) for x in range(5))
	return '%s.%s' % (path.join(tmp,n), fmt)

class _AbstractTransformer(object):
	def __init__(self, config, default_format):
		self.config = config
		self.default_format = default_format
		self.target_formats = config['target_formats']
		logger.info('Initialized %s.%s' % (__name__, self.__class__.__name__))

	def transform(self, src_fp, target_fp, image_request):
		'''
		Args:
			src_fp (str)
			target_fp (str)
			image (Image)
		Raises:
			ChangedFormatException:
				From 4.5 Format: "If neither [a file extension or HTTP Accept 
				header] are given, then the server should use a default format 
				of its own choosing."

				So 415 should never be an issue. Each _AbstractTransformer 
				impl will need to first try to fulfill the request, or else 
				fall back to a default format. ChangedFormatException should be 
				raised when the format is changed, and it will be up to the 
				caller to decide whether to continue or redirect first.
		'''
		e = self.__class__.__name__
		raise NotImplementedError('transform() not implemented for %s' % (cn,))

	def check_format(self, image_request):
		if image_request.format not in self.config['target_formats']:
			default = self.config[default_format]
			raise ChangedFormatException(image_request.format, self.default_format)

class JPG_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(JPG_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		self.check_format(image_request)

class TIF_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(TIF_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		self.check_format(image_request)

class JP2_Transformer(_AbstractTransformer):

	'''Exits if OSError is raised during init.
	'''
	def __init__(self, config, default_format):
		self.tmp_dp = config['tmp_dp']
		self.kdu_expand = config['kdu_expand']
		self.mkfifo = config['mkfifo']
		self.env = {
			'LD_LIBRARY_PATH' : config['kdu_libs'], 
			'PATH' : config['kdu_expand']
		}
		super(JP2_Transformer, self).__init__(config, default_format)

		try:
			if not path.exists(self.tmp_dp):
				makedirs(self.tmp_dp)
		except OSError as ose: 
			from sys import exit
			from os import strerror
			msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
			logger.fatal(msg)
			logger.fatal('Exiting')
			exit(77)

	def _region_to_kdu(self, region_param):
		'''
		Args:
			region_param (params.RegionParam)
		Raises:
			CalledProcessError

		Returns (str): e.g. '-region \{0.5,0.5\},\{0.5,0.5\}'
		'''
		arg = ''
		if region_param.mode != 'full':
			top = region_param.decimal_y
			left = region_param.decimal_x
			height = region_param.decimal_h
			width = region_param.decimal_w

			arg = '-region \{%s,%s\},\{%s,%s\}' % (top, left, height, width)
		logger.debug('kdu region parameter: %s' % (arg,))
		return arg


	def _rotation_to_kdu(self, rotation_param):
		'''Get a `-rotate` argument for the `convert` utility.

		Returns:
			str. E.g. `-rotate 180`.
		'''
		arg = ''
		if rotation_param.cannonical_uri_value != '0':
			arg = '-rotate %s' % (rotation_param.cannonical_uri_value,)
		logger.debug('kdu rotation parameter: %s' % (arg,))
		return arg

	def transform(self, src_fp, target_fp, image_request):
		self.check_format(image_request)

		if image_request.format not in self.target_formats:
			raise ChangedFormatException(self.default_format)

		# kdu writes to this:
		fifo_fp = make_tmp_fp(self.tmp_dp, 'bmp')

		# # make the named pipe

		mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
		logger.debug('Calling %s' % (mkfifo_call,))
		resp = subprocess.check_call(mkfifo_call, shell=True)
		if resp == 0:
			logger.debug('OK')
		# how to handle CalledProcessError?

		# kdu command
		q = '-quiet'
		i = '-i %s' % (src_fp,)
		o = '-o %s' % (fifo_fp,)
		region_arg = self._region_to_kdu(image_request.region_param)

		# kdu can do the rotation if it's a multiple of 90:
		rotate = int(image_request.rotation_param.uri_value)
		if rotate % 90 == 0:
			kdu_rotation_arg = self._rotation_to_kdu(image_request.rotation_param)
		else:
			kdu_rotation_arg = ''

		kdu_cmd = ' '.join((self.kdu_expand,q,i,region_arg,kdu_rotation_arg,o))

		logger.debug('Calling: %s' % (kdu_cmd,))

		# Start the kdu shellout. Blocks until the pipe is emptied
		kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1, 
			stderr=subprocess.PIPE,	env=self.env)

		f = open(fifo_fp, 'rb')
		logger.debug('Opened %s' % fifo_fp)

		# read from the named pipe
		# itertools.takewhile() ?
		p = Parser()
		while 1:
			s = f.read(1024)
			if not s:
				break
			p.feed(s)
		im = p.close() # a PIL.Image

		# finish kdu
		kdu_exit = kdu_expand_proc.wait()
		if kdu_exit != 0:
			map(logger.error, kdu_expand_proc.stderr)
		unlink(fifo_fp)

		if image_request.size_param.cannonical_uri_value != 'full':
			wh = (int(image_request.size_param.w),int(image_request.size_param.h))
			logger.debug(wh)
			im = im.resize(wh) # is there a way to change in place?

		if rotate % 90 != 0:
			im = im.rotate(rotate, expand=1)
			im = im.resize(wh)	
			# Here's a recipe for setting different background colors
			# http://stackoverflow.com/a/5253554/714478
			# Could take a hex color value (omit #) as a param:
			# http://stackoverflow.com/a/214657/714478

		if image_request.quality == 'grey':
			# im = grayscale(im) # TODO: confirm 8-bit
			im = im.convert('L')
		elif image_request.quality == 'bitonal':
			im = im.convert('1')

		if image_request.format == 'jpg':
			# see http://www.pythonware.com/library/pil/handbook/format-jpeg.htm
			im.save(target_fp)
		elif image_request.format == 'png':
			# see http://www.pythonware.com/library/pil/handbook/format-png.htm
			im.save(target_fp, optimize=True)


class ChangedFormatException(object):
	def __init__(self, to_ext):
		msg = 'Changed request format from %s to %s' % (from_ext, to_ext)
		super(ChangedFormatException, self).__init__()
		self.to_ext = to_ext
