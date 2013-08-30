# transformers.py
# -*- coding: utf-8 -*-

from PIL import Image
from PIL.ImageFile import Parser
from log_config import get_logger
from loris_exception import LorisException
from os import makedirs, path, unlink
import random
import string
import subprocess

logger = get_logger(__name__)

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
			image (ImageRequest)
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

	def _check_format(self, image_request):
		if image_request.format not in self.config['target_formats']:
			raise ChangedFormatException(self.default_format)

	@staticmethod
	def _round_rotation(rotation):
		'''Round the roation to the nearest 90. This method in no longer used by
		any of the OOTB transformers

		Args:
			rotation (str)
		'''
		return str(int(90 * round(float(rotation) / 90)))

	@staticmethod
	def _make_tmp_fp(tmp, fmt):
		n = ''.join(random.choice(string.ascii_lowercase) for x in range(5))
		return '%s.%s' % (path.join(tmp,n), fmt)

	@staticmethod
	def _derive_with_pil(im, target_fp, image_request, rotate=True):
		'''
		Once you have a PIL.Image, this can be used to do the IIIF operations.

		Args:
			im (PIL.Image)
			target_fp (str)
			image_request (ImageRequest)
			rotate (bool):
				True by default; can be set to False in case the rotation was
				done further upstream.
		Returns:
			void (puts an image at target_fp)

		'''
		if image_request.size_param.cannonical_uri_value != 'full':
			wh = (int(image_request.size_param.w),int(image_request.size_param.h))
			logger.debug(wh)
			im = im.resize(wh)

		if im.mode != "RGB":
			im = im.convert("RGB")

		if image_request.rotation_param.uri_value != '0' and rotate:
			r = int(image_request.rotation_param.uri_value)
			im = im.rotate(r, expand=1)

			# im = im.resize(wh)

			# Here's a recipe for setting different background colors
			# http://stackoverflow.com/a/5253554/714478
			# Could take a hex color value (omit #) as a param:
			# http://stackoverflow.com/a/214657/714478
			# Problem is that we'd need to cache each...and that logic would 
			# bleed around the app quite a bit for a not-often used feature.

		if image_request.quality == 'grey':
			im = im.convert('L')
		elif image_request.quality == 'bitonal':
			# not 1-bit w. JPG
			im = im.convert('1')

		if image_request.format == 'jpg':
			# see http://www.pythonware.com/library/pil/handbook/format-jpeg.htm
			im.save(target_fp, quality=90)
		elif image_request.format == 'png':
			# see http://www.pythonware.com/library/pil/handbook/format-png.htm
			im.save(target_fp, optimize=True, bits=256)


class JPG_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(JPG_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		self._check_format(image_request)
		im = Image.open(src_fp)
		JPG_Transformer._derive_with_pil(im, target_fp, image_request)


class TIF_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(TIF_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		self._check_format(image_request)
		im = Image.open(src_fp)
		TIF_Transformer._derive_with_pil(im, target_fp, image_request)

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
		self._check_format(image_request)

		# kdu writes to this:
		fifo_fp = JP2_Transformer._make_tmp_fp(self.tmp_dp, 'bmp')

		# make the named pipe
		mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
		logger.debug('Calling %s' % (mkfifo_call,))
		resp = subprocess.check_call(mkfifo_call, shell=True)
		if resp == 0:
			logger.debug('OK')
		# how to handle CalledProcessError; would have to be a 500?

		# kdu command
		q = '-quiet'
		i = '-i %s' % (src_fp,)
		o = '-o %s' % (fifo_fp,)
		region_arg = self._region_to_kdu(image_request.region_param)

		# kdu can do the rotation if it's a multiple of 90:
		
		if int(image_request.rotation_param.uri_value) % 90 == 0:
			rotate_downstream = False
			kdu_rotation_arg = self._rotation_to_kdu(image_request.rotation_param)
			kdu_cmd = ' '.join((self.kdu_expand,q,i,region_arg,kdu_rotation_arg,o))
		else:
			rotate_downstream = True
			kdu_cmd = ' '.join((self.kdu_expand,q,i,region_arg,o))


		logger.debug('Calling: %s' % (kdu_cmd,))

		# Start the kdu shellout. Blocks until the pipe is emptied
		kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1, 
			stderr=subprocess.PIPE,	env=self.env)

		f = open(fifo_fp, 'rb')
		logger.debug('Opened %s' % fifo_fp)

		# read from the named pipe
		# itertools.takewhile() ?
		p = Parser()
		while True:
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

		JP2_Transformer._derive_with_pil(im, target_fp, image_request, rotate=rotate_downstream)
		

class ChangedFormatException(Exception):
	def __init__(self, to_ext):
		super(ChangedFormatException, self).__init__()
		msg = 'Changed request format to %s' % (to_ext,)
		self.to_ext = to_ext
