# transformers.py
# -*- coding: utf-8 -*-

from PIL import Image
from PIL.ImageCms import profileToProfile
from PIL.ImageFile import Parser
from logging import getLogger
from loris_exception import LorisException
from math import ceil, log
from os import makedirs, path, unlink
from parameters import FULL_MODE
import cStringIO
import platform
import random
import string
import subprocess
import sys
try:
	from PIL.ImageCms import profileToProfile # Pillow
except ImportError:
	try:
		from ImageCms import profileToProfile # PIL
	except ImportError:
		pass


logger = getLogger(__name__)

class _AbstractTransformer(object):
	def __init__(self, config, default_format):
		self.config = config
		self.default_format = default_format
		self.target_formats = config['target_formats']
		logger.debug('Initialized %s.%s' % (__name__, self.__class__.__name__))

	def transform(self, src_fp, target_fp, image_request):
		'''
		Args:
			src_fp (str)
			target_fp (str)
			image (ImageRequest)
		'''
		e = self.__class__.__name__
		raise NotImplementedError('transform() not implemented for %s' % (cn,))

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
	def _scale_dim(dim,scale):
		return int(ceil(dim/float(scale)))

	@staticmethod
	def _get_closest_scale(req_w, req_h, full_w, full_h, scales):
		if req_w > full_w or req_h > full_h:
			return 1
		else:
			return max([s for s in scales \
				if _AbstractTransformer._scale_dim(full_w,s) >= req_w and \
					_AbstractTransformer._scale_dim(full_h,s) >= req_h])

	@staticmethod
	def _derive_with_pil(im, target_fp, image_request, rotate=True, crop=True):
		'''
		Once you have a PIL.Image, this can be used to do the IIIF operations.

		Args:
			im (PIL.Image)
			target_fp (str)
			image_request (ImageRequest)
			rotate (bool):
				True by default; can be set to False in case the rotation was
				done further upstream.
			crop (bool):
				True by default; can be set to False when the region was aleady 
				extracted further upstream.
		Returns:
			void (puts an image at target_fp)

		'''
		if crop and image_request.region_param.cannonical_uri_value != 'full':
			# For PIL: "The box is a 4-tuple defining the left, upper, right,
			# and lower pixel coordinate."
			box = (
				image_request.region_param.pixel_x,
				image_request.region_param.pixel_y,
				image_request.region_param.pixel_x+image_request.region_param.pixel_w,
				image_request.region_param.pixel_y+image_request.region_param.pixel_h
			)
			im = im.crop(box)

		# resize
		if image_request.size_param.cannonical_uri_value != 'full':
			wh = [int(image_request.size_param.w),int(image_request.size_param.h)]
			# if kdu did the rotation and it's 90 or 270 then reverse w & h
			if image_request.rotation_param.uri_value in ['90','270']:
				wh.reverse()

			logger.debug(wh)
			im = im.resize(wh, resample=Image.ANTIALIAS)

		if im.mode != "RGB":
			im = im.convert("RGB")

		if image_request.rotation_param.uri_value != '0' and rotate:
			r = 0-int(image_request.rotation_param.uri_value)
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
		elif image_request.format == 'gif':
			# see http://www.pythonware.com/library/pil/handbook/format-png.htm
			im.save(target_fp)


class JPG_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(JPG_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		im = Image.open(src_fp)
		JPG_Transformer._derive_with_pil(im, target_fp, image_request)

class TIF_Transformer(_AbstractTransformer):
	def __init__(self, config, default_format):
		super(TIF_Transformer, self).__init__(config, default_format)

	def transform(self, src_fp, target_fp, image_request):
		im = Image.open(src_fp)
		TIF_Transformer._derive_with_pil(im, target_fp, image_request)

class JP2_Transformer(_AbstractTransformer):

	'''Exits if OSError is raised during init.
	'''
	def __init__(self, config, default_format):
		self.tmp_dp = config['tmp_dp']
		self.kdu_expand = config['kdu_expand']
		self.mkfifo = config['mkfifo']
		self.map_profile_to_srgb = bool(config['map_profile_to_srgb'])
		self.env = {
			'LD_LIBRARY_PATH' : config['kdu_libs'], 
			'PATH' : config['kdu_expand']
		}

		if self.map_profile_to_srgb and \
			('PIL.ImageCms' not in sys.modules and 'ImageCms' not in sys.modules):
			logger.warn('Could not import profileToProfile from ImageCms.')
			logger.warn('Images will not have their embedded color profiles mapped to sSRGB.')
			self.map_profile_to_srgb = False
		else:
			self.srgb_profile_fp = config['srgb_profile_fp']
		
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

		super(JP2_Transformer, self).__init__(config, default_format)

	### These four methods re: kakadu are used in dev, tests, and by setup ###
	@staticmethod
	def local_kdu_expand_path():
		return 'bin/%s/%s/kdu_expand' % (platform.system(),platform.machine())
	#
	@staticmethod
	def local_libkdu_dir():
		return 'lib/%s/%s' % (platform.system(),platform.machine())
	#
	@staticmethod
	def libkdu_name():
		system = platform.system()
		if system == 'Linux':
			return 'libkdu_v72R.so'
		elif system == 'Darwin':
			return 'libkdu_v73R.dylib'
	#
	@staticmethod
	def local_libkdu_path():
		dir_ = JP2_Transformer.local_libkdu_dir()
		name = JP2_Transformer.libkdu_name()
		return '%s/%s' % (dir_,name)

	###                                ###                                  ###

	@staticmethod
	def _region_to_kdu(region_param):
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

	@staticmethod
	def _rotation_to_kdu(rotation_param):
		'''Get a `-rotate` argument for the `convert` utility.

		Returns:
			str. E.g. `-rotate 180`.
		'''
		arg = ''
		if rotation_param.cannonical_uri_value != '0':
			arg = '-rotate %s' % (rotation_param.cannonical_uri_value,)
		logger.debug('kdu rotation parameter: %s' % (arg,))
		return arg

	# @staticmethod
	# def _scale_to_kdu_reduce_arg(s):
	# 	return int(log(s, 2))

	@staticmethod
	def _scales_to_kdu_reduce(image_request):
		scales = image_request.info.scale_factors
		is_full_region = image_request.region_param.uri_value == FULL_MODE

		if scales and is_full_region:
			full_w = image_request.info.width
			full_h = image_request.info.height
			req_w = image_request.size_param.w
			req_h = image_request.size_param.h
			closest_scale = JP2_Transformer._get_closest_scale(req_w, req_h, full_w, full_h, scales)
			reduce_arg = int(log(closest_scale, 2))
			return '-reduce %d' % (reduce_arg,)
		else:
			return ''

	def transform(self, src_fp, target_fp, image_request):
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
		t = '-num_threads 8'
		i = '-i %s' % (src_fp,)
		o = '-o %s' % (fifo_fp,)

		region_arg = JP2_Transformer._region_to_kdu(image_request.region_param)
		reduce_arg = JP2_Transformer._scales_to_kdu_reduce(image_request)

		# kdu can do the rotation if it's a multiple of 90:
		if int(image_request.rotation_param.uri_value) % 90 == 0:
			rotate_downstream = False
			kdu_rotation_arg = JP2_Transformer._rotation_to_kdu(image_request.rotation_param)
			kdu_cmd = ' '.join((self.kdu_expand,q,i,t,region_arg,reduce_arg,kdu_rotation_arg,o))
		else:
			rotate_downstream = True
			kdu_cmd = ' '.join((self.kdu_expand,q,i,t,region_arg,reduce_arg,o))


		logger.debug('Calling: %s' % (kdu_cmd,))

		# Start the kdu shellout. Blocks until the pipe is empty
		kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1, 
			stderr=subprocess.PIPE,	env=self.env)

		f = open(fifo_fp, 'rb')
		logger.debug('Opened %s' % fifo_fp)

		# read from the named pipe
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

		if self.map_profile_to_srgb and image_request.info.color_profile_bytes:	 # i.e. is not None
			emb_profile = cStringIO.StringIO(image_request.info.color_profile_bytes)
			im = profileToProfile(im, emb_profile, self.srgb_profile_fp)

		JP2_Transformer._derive_with_pil(im, target_fp, image_request, rotate=rotate_downstream, crop=False)
