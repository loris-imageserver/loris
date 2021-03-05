from io import BytesIO
from logging import getLogger
from math import ceil, log
import os
from os import path
import platform
import subprocess
import tempfile

from PIL import Image
from PIL.ImageFile import Parser
from PIL.ImageOps import mirror

# This import is only used for converting embedded color profiles to sRGB,
# which is a user-configurable setting.  If they don't have this enabled,
# the failure of this import isn't catastrophic.
try:
    from PIL.ImageCms import profileToProfile, PyCMSError
    has_imagecms = True
except ImportError:
    has_imagecms = False

from loris.loris_exception import ConfigError, TransformException
from loris.parameters import FULL_MODE
from loris.utils import decode_bytes


logger = getLogger(__name__)


def _validate_color_profile_conversion_config(config):
    """
    Validate the config for setting up color profile conversion.
    """
    if not config.get('map_profile_to_srgb', False):
        return

    if config['map_profile_to_srgb'] and not config.get('srgb_profile_fp'):
        raise ConfigError(
            'When map_profile_to_srgb=True, you need to give the path to '
            'an sRGB color profile in the srgb_profile_fp setting.'
        )

    if config['map_profile_to_srgb'] and not has_imagecms:
        raise ConfigError(
            'When map_profile_to_srgb=True, you need to install Pillow with '
            'LittleCMS support.  See http://www.littlecms.com/ for instructions.'
        )


class _AbstractTransformer(object):
    def __init__(self, config):
        _validate_color_profile_conversion_config(config)
        self.config = config
        self.target_formats = config['target_formats']
        self.dither_bitonal_images = config['dither_bitonal_images']
        logger.debug('Initialized %s.%s', __name__, self.__class__.__name__)

    def transform(self, target_fp, image_request, image_info):
        '''
        Args:
            target_fp (str)
            image_request (ImageRequest)
            image_info (ImageInfo)
        '''
        cn = self.__class__.__name__
        raise NotImplementedError('transform() not implemented for %s' % (cn,))

    @property
    def map_profile_to_srgb(self):
        return self.config.get('map_profile_to_srgb', False)

    @property
    def srgb_profile_fp(self):
        return self.config.get('srgb_profile_fp')

    def _map_im_profile_to_srgb(self, im, input_profile):
        return profileToProfile(im, input_profile, self.srgb_profile_fp)

    def _derive_with_pil(self, im, target_fp, image_request, image_info, rotate=True, crop=True):
        '''
        Once you have a PIL.Image, this can be used to do the IIIF operations.

        Args:
            im (PIL.Image)
            target_fp (str)
            image_request (ImageRequest)
            image_info (ImageInfo)
            rotate (bool):
                True by default; can be set to False in case the rotation was
                done further upstream.
            crop (bool):
                True by default; can be set to False when the region was already
                extracted further upstream.
        Returns:
            void (puts an image at target_fp)

        '''
        region_param = image_request.region_param(image_info=image_info)

        if crop and region_param.canonical_uri_value != 'full':
            # For PIL: "The box is a 4-tuple defining the left, upper, right,
            # and lower pixel coordinate."
            box = (
                region_param.pixel_x,
                region_param.pixel_y,
                region_param.pixel_x + region_param.pixel_w,
                region_param.pixel_y + region_param.pixel_h
            )
            logger.debug('cropping to: %r', box)
            im = im.crop(box)

        # resize
        size_param = image_request.size_param(image_info=image_info)

        if size_param.canonical_uri_value != 'full':
            wh = [int(size_param.w), int(size_param.h)]
            logger.debug('Resizing to: %r', wh)
            im = im.resize(wh, resample=Image.ANTIALIAS)

        rotation_param = image_request.rotation_param()

        if rotation_param.mirror:
            im = mirror(im)

        try:
            if self.map_profile_to_srgb and 'icc_profile' in im.info:
                embedded_profile = BytesIO(im.info['icc_profile'])
                im = self._map_im_profile_to_srgb(im, embedded_profile)
        except PyCMSError as err:
            logger.warn(
                'Error converting %r (%r) to sRGB: %r',
                image_request.ident, image_info.src_img_fp, err
            )

        if rotation_param.rotation != '0' and rotate:
            r = 0 - float(rotation_param.rotation)

            # We need to convert pngs here and not below if we want a
            # transparent background (A == Alpha layer)
            if (
                float(rotation_param.rotation) % 90 != 0.0 and
                image_request.format == 'png'
            ):
                if image_request.quality in ('gray', 'bitonal'):
                    im = im.convert('LA')
                else:
                    im = im.convert('RGBA')

            im = im.rotate(r, expand=True)

        # If the source format is a PNG image with transparency (mode RGBA)
        # and we're writing as a non-transparent format (e.g. RGB), we need
        # to remove the transparency here.
        if (
            not im.mode.endswith('A') or
            (im.mode == 'RGBA' and image_request.format != 'png')
        ):
            if (
                im.mode != "RGB" and
                image_request.quality not in ('gray', 'bitonal')
            ):
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

        elif image_request.format == 'tif':
            # see http://pillow.readthedocs.io/en/latest/handbook/image-file-formats.html#tiff
            im.save(target_fp, compression='None')


class _PillowTransformer(_AbstractTransformer):

    def transform(self, target_fp, image_request, image_info):
        im = Image.open(image_info.src_img_fp)
        self._derive_with_pil(
            im=im,
            target_fp=target_fp,
            image_request=image_request,
            image_info=image_info
        )


class JPG_Transformer(_PillowTransformer):
    pass


class TIF_Transformer(_PillowTransformer):
    pass


class PNG_Transformer(_PillowTransformer):
    pass


class _AbstractJP2Transformer(_AbstractTransformer):
    '''
    Shared methods and configuration for the Kakadu and OpenJPEG transformers.

    Exits if OSError is raised during init.
    '''
    def __init__(self, config):
        self.tmp_dp = config['tmp_dp']

        try:
            os.makedirs(self.tmp_dp, exist_ok=True)
        except OSError as ose:
            # Almost certainly a permissions error on one of the required dirs
            from sys import exit
            from os import strerror
            logger.fatal('%s (%s)', strerror(ose.errno), ose.filename)
            logger.fatal('Exiting')
            exit(77)

        super().__init__(config)
        self.transform_timeout = config.get('timeout', 120)

    def _scale_dim(self, dim, scale):
        return int(ceil(dim/float(scale)))

    def _get_closest_scale(self, req_w, req_h, full_w, full_h, scales):
        if req_w > full_w or req_h > full_h:
            return 1
        else:
            return max([s for s in scales \
                if self._scale_dim(full_w,s) >= req_w and \
                    self._scale_dim(full_h,s) >= req_h])

    def _scales_to_reduce_arg(self, image_request, image_info):
        # Scales from JP2 levels, so even though these are from the tiles
        # info.json, it's easier than using the sizes from info.json
        scales = [s for t in image_info.tiles for s in t['scaleFactors']]
        is_full_region = image_request.region_param(image_info).mode == FULL_MODE
        arg = None
        if scales and is_full_region:
            full_w = image_info.width
            full_h = image_info.height
            req_w = image_request.size_param(image_info).w
            req_h = image_request.size_param(image_info).h
            closest_scale = self._get_closest_scale(req_w, req_h, full_w, full_h, scales)
            reduce_arg = int(log(closest_scale, 2))
            arg = str(reduce_arg)
        return arg

    def _process(self, transform_cmd, target_fp, image_request, image_info, tmp_img_fp):
        #generate tmp img with opj_decompress or kdu_expand
        try:
            subprocess.run(transform_cmd.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        except subprocess.CalledProcessError as e:
            msg = str(e)
            if e.stderr:
                msg = f'{msg}; stderr: {decode_bytes(e.stderr)}'
            if e.stdout:
                msg = f'{msg}; stdout: {decode_bytes(e.stdout)}'
            raise RuntimeError(msg)
        #now open that image with Pillow
        im = Image.open(tmp_img_fp)
        try:
            if self.map_profile_to_srgb and image_info.color_profile_bytes:
                emb_profile = BytesIO(image_info.color_profile_bytes)
                im = self._map_im_profile_to_srgb(im, emb_profile)
        except PyCMSError as err:
            logger.warn('Error converting %r to sRGB: %r', im, err)

        #now do any required transformations on the image
        self._derive_with_pil(
            im=im,
            target_fp=target_fp,
            image_request=image_request,
            image_info=image_info,
            crop=False
        )


class OPJ_JP2Transformer(_AbstractJP2Transformer):

    def __init__(self, config):
        self.opj_decompress = config['opj_decompress']
        self.env = None
        super().__init__(config)

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

    def transform(self, target_fp, image_request, image_info):
        # opj_decompress command
        region_arg = self._region_to_opj_arg(image_request.region_param(image_info))
        reg = '-d %s' % (region_arg,) if region_arg else ''
        reduce_arg = self._scales_to_reduce_arg(image_request, image_info)
        red = '-r %s' % (reduce_arg,) if reduce_arg else ''
        i = '-i %s' % (image_info.src_img_fp,)
        with tempfile.TemporaryDirectory(dir=self.tmp_dp) as tmp:
            tmp_img_fp = os.path.join(tmp, 'image.bmp')
            o = '-o %s' % (tmp_img_fp,)
            opj_cmd = ' '.join((self.opj_decompress,i,reg,red,o))
            try:
                self._process(opj_cmd, target_fp, image_request, image_info, tmp_img_fp)
            except Exception as e:
                logger.error(f'openjpeg transform error: {e}')
                raise TransformException('error generating derivative image: see log')


class KakaduJP2Transformer(_AbstractJP2Transformer):

    def __init__(self, config):
        self.kdu_expand = config['kdu_expand']
        self.num_threads = config['num_threads']
        self.env = {
            'LD_LIBRARY_PATH' : config['kdu_libs'],
            'PATH' : config['kdu_expand']
        }
        super().__init__(config)

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

            arg = '{%s,%s},{%s,%s}' % (top, left, height, width)
        logger.debug('kdu region parameter: %s', arg)
        return arg

    def transform(self, target_fp, image_request, image_info):
        # kdu command
        reduce_arg = self._scales_to_reduce_arg(image_request, image_info)
        red = '-reduce %s' % (reduce_arg,) if reduce_arg else ''
        region_arg = self._region_to_kdu_arg(image_request.region_param(image_info))
        reg = '-region %s' % (region_arg,) if region_arg else ''
        q = '-quiet'
        t = '-num_threads %s' % self.num_threads
        i = '-i %s' % image_info.src_img_fp
        with tempfile.TemporaryDirectory(dir=self.tmp_dp) as tmp:
            tmp_img_fp = os.path.join(tmp, 'image.bmp')
            o = '-o %s' % tmp_img_fp
            kdu_cmd = ' '.join((self.kdu_expand,q,i,t,reg,red,o))
            try:
                self._process(kdu_cmd, target_fp, image_request, image_info, tmp_img_fp)
            except Exception as e:
                logger.error(f'kakadu transform error: {e}')
                raise TransformException('error generating derivative image: see log')
