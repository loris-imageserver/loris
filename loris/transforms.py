# transformers.py
# -*- coding: utf-8 -*-

from PIL import Image
from PIL.ImageFile import Parser
from PIL.ImageOps import mirror
from logging import getLogger
from loris_exception import LorisException
from math import ceil, log
from os import makedirs, path, unlink, devnull
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
    from ImageCms import profileToProfile # PIL

logger = getLogger(__name__)

class _AbstractTransformer(object):
    def __init__(self, config):
        self.config = config
        self.target_formats = config['target_formats']
        self.dither_bitonal_images = config['dither_bitonal_images']
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
                True by default; can be set to False when the region was aleady 
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
            logger.debug('cropping to: %s' % (repr(box),))
            im = im.crop(box)

        # resize
        if image_request.size_param.canonical_uri_value != 'full':
            wh = [int(image_request.size_param.w),int(image_request.size_param.h)]
            logger.debug('Resizing to: %s' % (repr(wh),) )
            im = im.resize(wh, resample=Image.ANTIALIAS)

        if im.mode != "RGB":
            im = im.convert("RGB")

        if image_request.rotation_param.mirror:
            im = mirror(im)

        if image_request.rotation_param.rotation != '0' and rotate:
            r = 0-float(image_request.rotation_param.rotation)
            logger.debug('*'*80)
            logger.debug('Rotating (PIL syntax): %s' % (repr(r),))
            # We get a 1 px border at left and top with multiples of 90 with 
            # expand for some reason, so:
            expand = bool(r % 90)
            logger.debug('Expand: %s' % (repr(expand),))
            im = im.rotate(r, expand=expand) 

            # Here's a recipe for setting different background colors
            # http://stackoverflow.com/a/5253554/714478
            # Could take a hex color value (omit #) as a param:
            # http://stackoverflow.com/a/214657/714478
            # Problem is that we'd need to cache each...and that logic would 
            # bleed around the app quite a bit for a not-often used feature.

        if image_request.quality == 'gray':
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

class JPG_Transformer(_AbstractTransformer):
    def __init__(self, config):
        super(JPG_Transformer, self).__init__(config)

    def transform(self, src_fp, target_fp, image_request):
        im = Image.open(src_fp)
        self._derive_with_pil(im, target_fp, image_request)

class TIF_Transformer(_AbstractTransformer):
    def __init__(self, config):
        super(TIF_Transformer, self).__init__(config)

    def transform(self, src_fp, target_fp, image_request):
        im = Image.open(src_fp)
        self._derive_with_pil(im, target_fp, image_request)

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
            if not path.exists(self.tmp_dp):
                makedirs(self.tmp_dp)
        except OSError as ose: 
            # Almost certainly a permissions error on one of the required dirs
            from sys import exit
            from os import strerror
            msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
            logger.fatal(msg)
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
        is_full_region = image_request.region_param.uri_value == FULL_MODE
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
        '''Only used in dev, tests, and by setup.py
        '''
        return 'bin/%s/%s/opj_decompress' % (platform.system(),platform.machine())

    @staticmethod
    def local_libopenjp2_dir():
        '''Only used in dev, tests, and by setup.py
        '''
        return 'lib/%s/%s' % (platform.system(),platform.machine())

    @staticmethod
    def libopenjp2_name():
        '''Only used in dev, tests, and by setup.py
        '''
        system = platform.system()
        if system == 'Linux':
            return 'libopenjp2.so.2.1.0'
        elif system == 'Darwin':
            return 'libopenjp2.2.1.0.dylib'

    @staticmethod
    def local_libopenjp2_path():
        '''Only used in dev, tests, and by setup.py
        '''
        dir_ = OPJ_JP2Transformer.local_libopenjp2_dir()
        name = OPJ_JP2Transformer.libopenjp2_name()
        return '%s/%s' % (dir_,name)

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
        logger.debug('opj region parameter: %s' % (arg,))
        return arg

    def transform(self, src_fp, target_fp, image_request):
        # opj writes to this:
        fifo_fp = self._make_tmp_fp()

        # make the named pipe
        mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
        logger.debug('Calling %s' % (mkfifo_call,))
        resp = subprocess.check_call(mkfifo_call, shell=True)
        if resp != 0:
            logger.error('Problem with mkfifo')
        # how to handle CalledProcessError; would have to be a 500?

        # opj_decompress command
        i = '-i %s' % (src_fp,)
        o = '-o %s' % (fifo_fp,)
        region_arg = self._region_to_opj_arg(image_request.region_param)
        reg = '-d %s' % (region_arg,) if region_arg else ''
        reduce_arg = self._scales_to_reduce_arg(image_request)
        red = '-r %s' % (reduce_arg,) if reduce_arg else ''

        opj_cmd = ' '.join((self.opj_decompress,i,reg,red,o))

        logger.debug('Calling: %s' % (opj_cmd,))

        # Start the shellout. Blocks until the pipe is empty
        with open(devnull, 'w') as fnull:
            opj_decompress_proc = subprocess.Popen(opj_cmd, shell=True, bufsize=-1, 
                stderr=fnull, stdout=fnull, env=self.env)

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
        super(KakaduJP2Transformer, self).__init__(config)

    @staticmethod
    def local_kdu_expand_path():
        '''Only used in dev, tests, and by setup.py
        '''
        return 'bin/%s/%s/kdu_expand' % (platform.system(),platform.machine())

    @staticmethod
    def local_libkdu_dir():
        '''Only used in dev, tests, and by setup.py
        '''
        return 'lib/%s/%s' % (platform.system(),platform.machine())

    @staticmethod
    def libkdu_name():
        '''Only used in dev, tests, and by setup.py
        '''
        system = platform.system()
        if system == 'Linux':
            return 'libkdu_v74R.so'
        elif system == 'Darwin':
            return 'libkdu_v73R.dylib'

    @staticmethod
    def local_libkdu_path():
        '''Only used in dev, tests, and by setup.py
        '''
        dir_ = KakaduJP2Transformer.local_libkdu_dir()
        name = KakaduJP2Transformer.libkdu_name()
        return '%s/%s' % (dir_,name)

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
        logger.debug('kdu region parameter: %s' % (arg,))
        return arg

    def transform(self, src_fp, target_fp, image_request):

        # kdu writes to this:
        fifo_fp = self._make_tmp_fp()

        # make the named pipe
        mkfifo_call = '%s %s' % (self.mkfifo, fifo_fp)
        logger.debug('Calling %s' % (mkfifo_call,))
        resp = subprocess.check_call(mkfifo_call, shell=True)

        # kdu command
        q = '-quiet'
        t = '-num_threads %s' % (self.num_threads,)
        i = '-i %s' % (src_fp,)
        o = '-o %s' % (fifo_fp,)
        reduce_arg = self._scales_to_reduce_arg(image_request)
        red = '-reduce %s' % (reduce_arg,) if reduce_arg else ''
        region_arg = self._region_to_kdu_arg(image_request.region_param)
        reg = '-region %s' % (region_arg,) if region_arg else ''

        kdu_cmd = ' '.join((self.kdu_expand,q,i,t,reg,red,o))

        logger.debug('Calling: %s' % (kdu_cmd,))

        try:
            # Start the kdu shellout. Blocks until the pipe is empty
            kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1, 
                stderr=subprocess.PIPE, env=self.env)

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

            if self.map_profile_to_srgb and image_request.info.color_profile_bytes:  # i.e. is not None
                emb_profile = cStringIO.StringIO(image_request.info.color_profile_bytes)
                im = profileToProfile(im, emb_profile, self.srgb_profile_fp)

            self._derive_with_pil(im, target_fp, image_request, crop=False)
        except:
            raise
        finally:
            if kdu_expand_proc.poll() is None:
                kdu_expand_proc.kill()
            unlink(fifo_fp)

