# transformers.py
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import multiprocessing
from logging import getLogger
from math import ceil, log
from os import path, unlink, devnull
import cStringIO
import platform
import random
import string
import subprocess
import sys

from PIL import Image
from PIL.ImageFile import Parser
from PIL.ImageOps import mirror

try:
    from PIL.ImageCms import profileToProfile  # Pillow
except ImportError:
    from ImageCms import profileToProfile  # PIL

from loris.loris_exception import TransformException
from loris.parameters import FULL_MODE
from loris.utils import mkdir_p

logger = getLogger(__name__)

class _AbstractTransformer(object):
    def __init__(self, config):
        self.config = config
        self.target_formats = config['target_formats']
        self.dither_bitonal_images = config['dither_bitonal_images']
        logger.debug('Initialized %s.%s', __name__, self.__class__.__name__)

    def transform(self, src_fp, target_fp, image_request):
        '''
        Args:
            src_fp (str)
            target_fp (str)
            image (ImageRequest)
        '''
        cn = self.__class__.__name__
        raise NotImplementedError('transform() not implemented for %s' % (cn,))

    def _derive_with_pil(self, im, target_fp, image_request, rotate=True, crop=True):
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
                True by default; can be set to False when the region was already
                extracted further upstream.
        Returns:
            void (puts an image at target_fp)

        '''

        if crop and image_request.region_param.canonical_uri_value != 'full':
            # For PIL: "The box is a 4-tuple defining the left, upper, right,
            # and lower pixel coordinate."
            box = (
                image_request.region_param.pixel_x,
                image_request.region_param.pixel_y,
                image_request.region_param.pixel_x+image_request.region_param.pixel_w,
                image_request.region_param.pixel_y+image_request.region_param.pixel_h
            )
            logger.debug('cropping to: %r', box)
            im = im.crop(box)

        # resize
        if image_request.size_param.canonical_uri_value != 'full':
            wh = [int(image_request.size_param.w),int(image_request.size_param.h)]
            logger.debug('Resizing to: %r', wh)
            im = im.resize(wh, resample=Image.ANTIALIAS)


        if image_request.rotation_param.mirror:
            im = mirror(im)

        if image_request.rotation_param.rotation != '0' and rotate:
            r = 0-float(image_request.rotation_param.rotation)

            # We need to convert pngs here and not below if we want a
            # transparent background (A == Alpha layer)
            if float(image_request.rotation_param.rotation) % 90 != 0.0 and \
                image_request.format == 'png':

                if image_request.quality in ('gray', 'bitonal'):
                    im = im.convert('LA')
                else:
                    im = im.convert('RGBA')

            im = im.rotate(r, expand=True)

        if not im.mode.endswith('A'):
            if im.mode != "RGB" and not image_request.quality in ('gray', 'bitonal'):
                im = im.convert("RGB")

            elif image_request.quality == 'gray':
                im = im.convert('L')

            elif image_request.quality == 'bitonal':
                # not 1-bit w. JPG
                dither = Image.FLOYDSTEINBERG if self.dither_bitonal_images else Image.NONE
                im = im.convert('1', dither=dither)

        if image_request.format == 'jpg':
            # see http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html#jpeg
            im.save(target_fp, quality=90)

        elif image_request.format == 'png':
            # see http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html#png
            im.save(target_fp, optimize=True, bits=256)

        elif image_request.format == 'gif':
            # see http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html#gif
            im.save(target_fp)

        elif image_request.format == 'webp':
            # see http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html#webp
            im.save(target_fp, quality=90)


class _PillowTransformer(_AbstractTransformer):
    def __init__(self, config):
        super(_PillowTransformer, self).__init__(config)

    def transform(self, src_fp, target_fp, image_request):
        im = Image.open(src_fp)
        self._derive_with_pil(im, target_fp, image_request)

class JPG_Transformer(_PillowTransformer):
    def __init__(self, config): super(JPG_Transformer, self).__init__(config)

class TIF_Transformer(_PillowTransformer):
    def __init__(self, config): super(TIF_Transformer, self).__init__(config)

class PNG_Transformer(_PillowTransformer):
    def __init__(self, config): super(PNG_Transformer, self).__init__(config)

class _AbstractJP2Transformer(_AbstractTransformer):
    '''
    Shared methods and configuration for the Kakadu and OpenJPEG transformers.

    Exits if OSError is raised during init.
    '''
    def __init__(self, config):
        self.map_profile_to_srgb = bool(config['map_profile_to_srgb'])
        self.mkfifo = config['mkfifo']
        self.tmp_dp = config['tmp_dp']

        if self.map_profile_to_srgb and \
            ('PIL.ImageCms' not in sys.modules and 'ImageCms' not in sys.modules):
            logger.warn('Could not import profileToProfile from ImageCms.')
            logger.warn('Images will not have their embedded color profiles mapped to sSRGB.')
            self.map_profile_to_srgb = False
        else:
            self.srgb_profile_fp = config['srgb_profile_fp']

        try:
            mkdir_p(self.tmp_dp)
        except OSError as ose:
            # Almost certainly a permissions error on one of the required dirs
            from sys import exit
            from os import strerror
            logger.fatal('%s (%s)', strerror(ose.errno), ose.filename)
            logger.fatal('Exiting')
            exit(77)

        super(_AbstractJP2Transformer, self).__init__(config)

    def _make_tmp_fp(self, fmt='bmp'):
        n = ''.join(random.choice(string.ascii_lowercase) for x in range(5))
        return '%s.%s' % (path.join(self.tmp_dp, n), fmt)

    def _scale_dim(self, dim, scale):
        return int(ceil(dim/float(scale)))

    def _get_closest_scale(self, req_w, req_h, full_w, full_h, scales):
        if req_w > full_w or req_h > full_h:
            return 1
        else:
            return max([s for s in scales \
                if self._scale_dim(full_w,s) >= req_w and \
                    self._scale_dim(full_h,s) >= req_h])

    def _scales_to_reduce_arg(self, image_request):
        # Scales from from JP2 levels, so even though these are from the tiles
        # info.json, it's easier than using the sizes from info.json
        scales = [s for t in image_request.info.tiles for s in t['scaleFactors']]
        is_full_region = image_request.region_param.mode == FULL_MODE
        arg = None
        if scales and is_full_region:
            full_w = image_request.info.width
            full_h = image_request.info.height
            req_w = image_request.size_param.w
            req_h = image_request.size_param.h
            closest_scale = self._get_closest_scale(req_w, req_h, full_w, full_h, scales)
            reduce_arg = int(log(closest_scale, 2))
            arg = str(reduce_arg)
        return arg

class OPJ_JP2Transformer(_AbstractJP2Transformer):
    def __init__(self, config):
        self.opj_decompress = config['opj_decompress']
        self.env = {
            'LD_LIBRARY_PATH' : config['opj_libs'],
            'PATH' : config['opj_decompress']
        }
        super(OPJ_JP2Transformer, self).__init__(config)

    @staticmethod
    def local_opj_decompress_path():
        '''Only used in dev and tests.
        '''
        return 'bin/%s/%s/opj_decompress' % (platform.system(),platform.machine())

    @staticmethod
    def local_libopenjp2_dir():
        '''Only used in dev and tests.
        '''
        return 'lib/%s/%s' % (platform.system(),platform.machine())

    def _region_to_opj_arg(self, region_param):
        '''
        Args:
            region_param (params.RegionParam)

        Returns (str): e.g. 'x0,y0,x1,y1'
        '''
        arg = None
        if region_param.mode != 'full':
            x0 = region_param.pixel_x
            y0 = region_param.pixel_y
            x1 = region_param.pixel_x + region_param.pixel_w
            y1 = region_param.pixel_y + region_param.pixel_h
            arg = ','.join(map(str, (x0, y0, x1, y1)))
        logger.debug('opj region parameter: %s', arg)
        return arg

    def transform(self, src_fp, target_fp, image_request):
        # opj writes to this:
        fifo_fp = self._make_tmp_fp()

        # make the named pipe
        mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
        logger.debug('Calling %s', mkfifo_call)
        resp = subprocess.check_call(mkfifo_call, shell=True)
        if resp != 0:
            logger.error('Problem with mkfifo')
        # how to handle CalledProcessError; would have to be a 500?

        # opj_decompress command
        i = '-i "%s"' % (src_fp,)
        o = '-o %s' % (fifo_fp,)
        region_arg = self._region_to_opj_arg(image_request.region_param)
        reg = '-d %s' % (region_arg,) if region_arg else ''
        reduce_arg = self._scales_to_reduce_arg(image_request)
        red = '-r %s' % (reduce_arg,) if reduce_arg else ''

        opj_cmd = ' '.join((self.opj_decompress,i,reg,red,o))

        logger.debug('Calling: %s', opj_cmd)

        # Start the shellout. Blocks until the pipe is empty
        with open(devnull, 'w') as fnull:
            opj_decompress_proc = subprocess.Popen(opj_cmd, shell=True, bufsize=-1,
                stderr=fnull, stdout=fnull, env=self.env)

        with open(fifo_fp, 'rb') as f:
            # read from the named pipe
            p = Parser()
            while True:
                s = f.read(1024)
                if not s:
                    break
                p.feed(s)
            im = p.close() # a PIL.Image

        # finish opj
        opj_exit = opj_decompress_proc.wait()
        if opj_exit != 0:
            map(logger.error, opj_decompress_proc.stderr)
        unlink(fifo_fp)

        if self.map_profile_to_srgb and image_request.info.color_profile_bytes:  # i.e. is not None
            emb_profile = cStringIO.StringIO(image_request.info.color_profile_bytes)
            im = profileToProfile(im, emb_profile, self.srgb_profile_fp)

        self._derive_with_pil(im, target_fp, image_request, crop=False)

class KakaduJP2Transformer(_AbstractJP2Transformer):

    def __init__(self, config):
        self.kdu_expand = config['kdu_expand']
        self.num_threads = config['num_threads']
        self.env = {
            'LD_LIBRARY_PATH' : config['kdu_libs'],
            'PATH' : config['kdu_expand']
        }
        self.transform_timeout = config.get('timeout', 120)
        super(KakaduJP2Transformer, self).__init__(config)

    @staticmethod
    def local_kdu_expand_path():
        '''Only used in dev and tests.
        '''
        return 'bin/%s/%s/kdu_expand' % (platform.system(),platform.machine())

    @staticmethod
    def local_libkdu_dir():
        '''Only used in dev and tests.
        '''
        return 'lib/%s/%s' % (platform.system(),platform.machine())

    def _region_to_kdu_arg(self, region_param):
        '''
        Args:
            region_param (params.RegionParam)

        Returns (str): e.g. '\{0.5,0.5\},\{0.5,0.5\}'
        '''
        arg = None
        if region_param.mode != 'full':
            top = region_param.decimal_y
            left = region_param.decimal_x
            height = region_param.decimal_h
            width = region_param.decimal_w

            arg = '\{%s,%s\},\{%s,%s\}' % (top, left, height, width)
        logger.debug('kdu region parameter: %s', arg)
        return arg

    def _run_transform(self, target_fp, image_request, kdu_cmd, fifo_fp):
        try:
            # Start the kdu shellout. Blocks until the pipe is empty
            kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1,
                stderr=subprocess.PIPE, env=self.env)
            with open(fifo_fp, 'rb') as f:
                # read from the named pipe
                p = Parser()
                while True:
                    s = f.read(1024)
                    if not s:
                        break
                    p.feed(s)
                im = p.close() # a PIL.Image
        finally:
            stdoutdata, stderrdata = kdu_expand_proc.communicate()
            kdu_exit = kdu_expand_proc.returncode
            if kdu_exit != 0:
                map(logger.error, stderrdata)
            unlink(fifo_fp)

        if self.map_profile_to_srgb and image_request.info.color_profile_bytes:  # i.e. is not None
            emb_profile = cStringIO.StringIO(image_request.info.color_profile_bytes)
            im = profileToProfile(im, emb_profile, self.srgb_profile_fp)

        self._derive_with_pil(im, target_fp, image_request, crop=False)

    def transform(self, src_fp, target_fp, image_request):
        fifo_fp = self._make_tmp_fp()
        mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
        subprocess.check_call(mkfifo_call, shell=True)

        # kdu command
        q = '-quiet'
        t = '-num_threads %s' % self.num_threads
        i = '-i "%s"' % src_fp
        o = '-o %s' % fifo_fp
        reduce_arg = self._scales_to_reduce_arg(image_request)
        red = '-reduce %s' % (reduce_arg,) if reduce_arg else ''
        region_arg = self._region_to_kdu_arg(image_request.region_param)
        reg = '-region %s' % (region_arg,) if region_arg else ''
        kdu_cmd = ' '.join((self.kdu_expand,q,i,t,reg,red,o))

        process = multiprocessing.Process(target=self._run_transform,
                                          args=(target_fp, image_request, kdu_cmd, fifo_fp))
        process.start()
        process.join(self.transform_timeout)
        if process.is_alive():
            logger.info('terminating process for %s, %s', src_fp, target_fp)
            process.terminate()
            if path.exists(fifo_fp):
                unlink(fifo_fp)
            raise TransformException('transform process timed out')
