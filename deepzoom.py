#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#  Deep Zoom Tools
#
#  Copyright (c) 2008-2011, OpenZoom <http://openzoom.org>
#  Copyright (c) 2008-2011, Daniel Gasienica <daniel@gasienica.ch>
#  Copyright (c) 2010, Boris Bluntschli <boris@bluntschli.ch>
#  Copyright (c) 2008, Kapil Thangavelu <kapil.foss@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without modification,
#  are permitted provided that the following conditions are met:
#
#      1. Redistributions of source code must retain the above copyright notice,
#         this list of conditions and the following disclaimer.
#
#      2. Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#
#      3. Neither the name of OpenZoom nor the names of its contributors may be used
#         to endorse or promote products derived from this software without
#         specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#  ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import math
import optparse
import os
import PIL.Image
import shutil

try:
    import cStringIO
    StringIO = cStringIO
except ImportError:
    import StringIO

import sys
import time
import urllib
import warnings
import xml.dom.minidom

from collections import deque


NS_DEEPZOOM = 'http://schemas.microsoft.com/deepzoom/2008'

DEFAULT_RESIZE_FILTER = PIL.Image.ANTIALIAS
DEFAULT_IMAGE_FORMAT = 'jpg'

RESIZE_FILTERS = {
    'cubic': PIL.Image.CUBIC,
    'bilinear': PIL.Image.BILINEAR,
    'bicubic': PIL.Image.BICUBIC,
    'nearest': PIL.Image.NEAREST,
    'antialias': PIL.Image.ANTIALIAS,
    }

IMAGE_FORMATS = {
    'jpg': 'jpg',
    'png': 'png',
    }


class DeepZoomImageDescriptor(object):
    def __init__(self, width=None, height=None,
                 tile_size=254, tile_overlap=1, tile_format='jpg'):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.tile_format = tile_format
        self._num_levels = None

    def open(self, source):
        """Intialize descriptor from an existing descriptor file."""
        doc = xml.dom.minidom.parse(safe_open(source))
        image = doc.getElementsByTagName('Image')[0]
        size = doc.getElementsByTagName('Size')[0]
        self.width = int(size.getAttribute('Width'))
        self.height = int(size.getAttribute('Height'))
        self.tile_size = int(image.getAttribute('TileSize'))
        self.tile_overlap = int(image.getAttribute('Overlap'))
        self.tile_format = image.getAttribute('Format')

    def marshal(self): # pulled out of save() for loris
        doc = xml.dom.minidom.Document()
        image = doc.createElementNS(NS_DEEPZOOM, 'Image')
        image.setAttribute('xmlns', NS_DEEPZOOM)
        image.setAttribute('TileSize', str(self.tile_size))
        image.setAttribute('Overlap', str(self.tile_overlap))
        image.setAttribute('Format', str(self.tile_format))
        size = doc.createElementNS(NS_DEEPZOOM, 'Size')
        size.setAttribute('Width', str(self.width))
        size.setAttribute('Height', str(self.height))
        image.appendChild(size)
        doc.appendChild(image)
        descriptor = doc.toxml(encoding='UTF-8')
        return descriptor

    def save(self, destination):
        """Save descriptor file."""
        file = open(destination, 'w')
        descriptor = self.marshal()
        file.write(descriptor)
        file.close()

    @classmethod
    def remove(self, filename):
        """Remove descriptor file (DZI) and tiles folder."""
        _remove(filename)

    @property
    def num_levels(self):
        """Number of levels in the pyramid."""
        if self._num_levels is None:
            max_dimension = max(self.width, self.height)
            self._num_levels = int(math.ceil(math.log(max_dimension, 2))) + 1
        return self._num_levels

    def get_scale(self, level):
        """Scale of a pyramid level."""
        assert 0 <= level and level < self.num_levels, 'Invalid pyramid level'
        max_level = self.num_levels - 1
        return math.pow(0.5, max_level - level)

    def get_dimensions(self, level):
        """Dimensions of level (width, height)"""
        assert 0 <= level and level < self.num_levels, 'Invalid pyramid level'
        scale = self.get_scale(level)
        width = int(math.ceil(self.width * scale))
        height = int(math.ceil(self.height * scale))
        return (width, height)

    def get_num_tiles(self, level):
        """Number of tiles (columns, rows)"""
        assert 0 <= level and level < self.num_levels, 'Invalid pyramid level'
        w, h = self.get_dimensions( level )
        return (int(math.ceil(float(w) / self.tile_size)),
                int(math.ceil(float(h) / self.tile_size)))

    def get_tile_bounds(self, level, column, row):
        """Bounding box of the tile (x1, y1, x2, y2)"""
        assert 0 <= level and level < self.num_levels, 'Invalid pyramid level'
        offset_x = 0 if column == 0 else self.tile_overlap
        offset_y = 0 if row == 0 else self.tile_overlap
        x = (column * self.tile_size) - offset_x
        y = (row * self.tile_size) - offset_y
        level_width, level_height = self.get_dimensions(level)
        w = self.tile_size + (1 if column == 0 else 2) * self.tile_overlap
        h = self.tile_size + (1 if row == 0 else 2) * self.tile_overlap
        w = min(w, level_width  - x)
        h = min(h, level_height - y)
        return (x, y, x + w, y + h)


class DeepZoomCollection(object):
    def __init__(self, filename, image_quality=0.8, max_level=7,
                tile_size=256, tile_format='jpg', items=[]):
        self.source = filename
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.items = deque(items)
        self.next_item_id = len(self.items)
        # XML
        self.doc = xml.dom.minidom.Document()
        collection = self.doc.createElementNS(NS_DEEPZOOM, 'Collection')
        collection.setAttribute('xmlns', NS_DEEPZOOM)
        collection.setAttribute('MaxLevel', str(self.max_level))
        collection.setAttribute('TileSize', str(self.tile_size))
        collection.setAttribute('Format', str(self.tile_format))
        collection.setAttribute('Quality', str(self.image_quality))
        items = self.doc.createElementNS(NS_DEEPZOOM, 'Items')
        collection.appendChild(items)
        collection.setAttribute('NextItemId', str(self.next_item_id))
        self.doc.appendChild(collection)

    @classmethod
    def from_file(self, filename):
        """Open collection descriptor."""
        doc = xml.dom.minidom.parse(safe_open(filename))
        collection = doc.getElementsByTagName('Collection')[0]
        image_quality = float(collection.getAttribute('Quality'))
        max_level = int(collection.getAttribute('MaxLevel'))
        tile_size = int(collection.getAttribute('TileSize'))
        tile_format = collection.getAttribute('Format')
        items = [DeepZoomCollectionItem.from_xml(item) for item
                    in doc.getElementsByTagName('I')]

        collection = DeepZoomCollection(filename,
                                        image_quality=image_quality,
                                        max_level=max_level,
                                        tile_size=tile_size,
                                        tile_format=tile_format,
                                        items=items)
        return collection


    @classmethod
    def remove(self, filename):
        """Remove collection file (DZC) and tiles folder."""
        _remove(filename)

    def append(self, source):
        descriptor = DeepZoomImageDescriptor()
        descriptor.open(source)
        item = DeepZoomCollectionItem(source, descriptor.width, descriptor.height,
                                     id=self.next_item_id)
        self.items.append(item)
        self.next_item_id += 1

    def save(self, pretty_print_xml=False):
        """Save collection descriptor."""
        collection = self.doc.getElementsByTagName('Collection')[0]
        items = self.doc.getElementsByTagName('Items')[0]
        while len(self.items) > 0:
            item = self.items.popleft()
            i = self.doc.createElementNS(NS_DEEPZOOM, 'I')
            i.setAttribute('Id', str(item.id))
            i.setAttribute('N', str(item.id))
            i.setAttribute('Source', item.source)
            # Size
            size = self.doc.createElementNS(NS_DEEPZOOM, 'Size')
            size.setAttribute('Width', str(item.width))
            size.setAttribute('Height', str(item.height))
            i.appendChild(size)
            items.appendChild(i)
            self._append_image(item.source, item.id)
        collection.setAttribute('NextItemId', str(self.next_item_id))
        with open(self.source, 'w') as f:
            if pretty_print_xml:
                xml = self.doc.toprettyxml(encoding='UTF-8')
            else:
                xml = self.doc.toxml(encoding='UTF-8')
            f.write(xml)

    def _append_image(self, path, i):
        descriptor = DeepZoomImageDescriptor()
        descriptor.open(path)
        files_path = _get_or_create_path(_get_files_path(self.source))
        for level in reversed(xrange(self.max_level + 1)):
            level_path = _get_or_create_path('%s/%s'%(files_path, level))
            level_size = 2**level
            images_per_tile = int(math.floor(self.tile_size / level_size))
            column, row = self.get_tile_position(i, level, self.tile_size)
            tile_path = '%s/%s_%s.%s'%(level_path, column, row, self.tile_format)
            if not os.path.exists(tile_path):
                tile_image = PIL.Image.new('RGB', (self.tile_size, self.tile_size))
                q = int(self.image_quality * 100)
                tile_image.save(tile_path, 'JPEG', quality=q)
            tile_image = PIL.Image.open(tile_path)
            source_path = '%s/%s/%s_%s.%s'%(_get_files_path(path), level, 0, 0,
                                            descriptor.tile_format)
            # Local
            if os.path.exists(source_path):
                try:
                    source_image = PIL.Image.open(safe_open(source_path))
                except IOError:
                    warnings.warn('Skipped invalid level: %s' % source_path)
                    continue
            # Remote
            else:
                if level == self.max_level:
                    try:
                        source_image = PIL.Image.open(safe_open(source_path))
                    except IOError:
                        warnings.warn('Skipped invalid image: %s' % source_path)
                        return
                    # Expected width & height of the tile
                    e_w, e_h = descriptor.get_dimensions(level)
                    # Actual width & height of the tile
                    w, h = source_image.size
                    # Correct tile because of IIP bug where low-level tiles
                    # have wrong dimensions (they are too large)
                    if w != e_w or h != e_h:
                        # Resize incorrect tile to correct size
                        source_image = source_image.resize((e_w, e_h), PIL.Image.ANTIALIAS)
                        # Store new dimensions
                        w, h = e_w, e_h
                else:
                    w = int(math.ceil(w * 0.5))
                    h = int(math.ceil(h * 0.5))
                    source_image.thumbnail((w, h), PIL.Image.ANTIALIAS)
            column, row = self.get_position(i)
            x = (column % images_per_tile) * level_size
            y = (row % images_per_tile) * level_size
            tile_image.paste(source_image, (x, y))
            tile_image.save(tile_path)

    def get_position(self, z_order):
        """Returns position (column, row) from given Z-order (Morton number.)"""
        column = 0
        row = 0
        for i in xrange(0, 32, 2):
            offset = i / 2
            # column
            column_offset = i
            column_mask = 1 << column_offset
            column_value = (z_order & column_mask) >> column_offset
            column |= column_value << offset
            #row
            row_offset = i + 1
            row_mask = 1 << row_offset
            row_value = (z_order & row_mask) >> row_offset
            row |= row_value << offset
        return int(column), int(row)

    def get_z_order(self, column, row):
        """Returns the Z-order (Morton number) from given position."""
        z_order = 0
        for i in xrange(32):
            z_order |= (column & 1 << i) << i | (row & 1 << i) << (i + 1)
        return z_order

    def get_tile_position(self, z_order, level, tile_size):
        level_size = 2**level
        x, y = self.get_position(z_order)
        return (int(math.floor((x * level_size) / tile_size)),
                int(math.floor((y * level_size) / tile_size)))


class DeepZoomCollectionItem(object):
    def __init__(self, source, width, height, id=0):
        self.id = id
        self.source = source
        self.width = width
        self.height = height

    @classmethod
    def from_xml(cls, xml):
        id = int(xml.getAttribute('Id'))
        source = xml.getAttribute('Source')
        size = xml.getElementsByTagName('Size')[0]
        width = int(size.getAttribute('Width'))
        height = int(size.getAttribute('Height'))
        return DeepZoomCollectionItem(source, width, height, id)


class ImageCreator(object):
    """Creates Deep Zoom images."""
    def __init__(self, tile_size=254, tile_overlap=1, tile_format='jpg',
                 image_quality=0.8, resize_filter=None, copy_metadata=False):
        self.tile_size = int(tile_size)
        self.tile_format = tile_format
        self.tile_overlap = _clamp(int(tile_overlap), 0, 10)
        self.image_quality = _clamp(image_quality, 0, 1.0)
        if not tile_format in IMAGE_FORMATS:
            self.tile_format = DEFAULT_IMAGE_FORMAT
        self.resize_filter = resize_filter
        self.copy_metadata = copy_metadata

    def get_image(self, level):
        """Returns the bitmap image at the given level."""
        assert 0 <= level and level < self.descriptor.num_levels, 'Invalid pyramid level'
        width, height = self.descriptor.get_dimensions(level)
        # don't transform to what we already have
        if self.descriptor.width == width and self.descriptor.height == height:
            return self.image
        if (self.resize_filter is None) or (self.resize_filter not in RESIZE_FILTERS):
            return self.image.resize((width, height), PIL.Image.ANTIALIAS)
        return self.image.resize((width, height), RESIZE_FILTERS[self.resize_filter])

    def tiles(self, level):
        """Iterator for all tiles in the given level. Returns (column, row) of a tile."""
        columns, rows = self.descriptor.get_num_tiles(level)
        for column in xrange(columns):
            for row in xrange(rows):
                yield (column, row)

    def create(self, source, destination):
        """Creates Deep Zoom image from source file and saves it to destination."""
        self.image = PIL.Image.open(safe_open(source))
        width, height = self.image.size
        self.descriptor = DeepZoomImageDescriptor(width=width,
                                                  height=height,
                                                  tile_size=self.tile_size,
                                                  tile_overlap=self.tile_overlap,
                                                  tile_format=self.tile_format)
        # Create tiles
        image_files = _get_or_create_path(_get_files_path(destination))
        for level in xrange(self.descriptor.num_levels):
            level_dir = _get_or_create_path(os.path.join(image_files, str(level)))
            level_image = self.get_image(level)
            for (column, row) in self.tiles(level):
                bounds = self.descriptor.get_tile_bounds(level, column, row)
                tile = level_image.crop(bounds)
                format = self.descriptor.tile_format
                tile_path = os.path.join(level_dir,
                                         '%s_%s.%s'%(column, row, format))
                tile_file = open(tile_path, 'wb')
                if self.descriptor.tile_format == 'jpg':
                    jpeg_quality = int(self.image_quality * 100)
                    tile.save(tile_file, 'JPEG', quality=jpeg_quality)
                else:
                    tile.save(tile_file)
        # Create descriptor
        self.descriptor.save(destination)


class CollectionCreator(object):
    """Creates Deep Zoom collections."""
    def __init__(self, image_quality=0.8, tile_size=256,
                 max_level=7, tile_format='jpg', copy_metadata=False):
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        # TODO
        self.copy_metadata = copy_metadata

    def create(self, images, destination):
        """Creates a Deep Zoom collection from a list of images."""
        collection = DeepZoomCollection(destination,
                                        image_quality=self.image_quality,
                                        max_level=self.max_level,
                                        tile_size=self.tile_size,
                                        tile_format=self.tile_format)
        for image in images:
            collection.append(image)
        collection.save()

################################################################################

def retry(attempts, backoff=2):
    """Retries a function or method until it returns or
    the number of attempts has been reached."""

    if backoff <= 1:
        raise ValueError('backoff must be greater than 1')

    attempts = int(math.floor(attempts))
    if attempts < 0:
        raise ValueError('attempts must be 0 or greater')

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            last_exception = None
            for _ in xrange(attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as exception:
                    last_exception = exception
                    time.sleep(backoff**(attempts + 1))
            raise last_exception
        return f_retry
    return deco_retry

def _get_or_create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def _clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    return val

def _get_files_path(path):
    return os.path.splitext(path)[0] + '_files'

def _remove(path):
    os.remove(path)
    tiles_path = _get_files_path(path)
    shutil.rmtree(tiles_path)

@retry(6)
def safe_open(path):
    return StringIO.StringIO(urllib.urlopen(path).read())

################################################################################

def main():
    parser = optparse.OptionParser(usage='Usage: %prog [options] filename')

    parser.add_option('-d', '--destination', dest='destination',
                      help='Set the destination of the output.')
    parser.add_option('-s', '--tile_size', dest='tile_size', type='int',
                      default=254, help='Size of the tiles. Default: 254')
    parser.add_option('-f', '--tile_format', dest='tile_format',
                      default=DEFAULT_IMAGE_FORMAT, help='Image format of the tiles (jpg or png). Default: jpg')
    parser.add_option('-o', '--tile_overlap', dest='tile_overlap', type='int',
                      default=1, help='Overlap of the tiles in pixels (0-10). Default: 1')
    parser.add_option('-q', '--image_quality', dest='image_quality', type='float',
                      default=0.8, help='Quality of the image output (0-1). Default: 0.8')
    parser.add_option('-r', '--resize_filter', dest='resize_filter', default=DEFAULT_RESIZE_FILTER,
                      help='Type of filter for resizing (bicubic, nearest, bilinear, antialias (best). Default: antialias')

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(1)

    source = args[0]

    if not options.destination:
        if os.path.exists(source):
            options.destination = os.path.splitext(source)[0] + '.dzi'
        else:
            options.destination = os.path.splitext(os.path.basename(source))[0] + '.dzi'
    if options.resize_filter and options.resize_filter in RESIZE_FILTERS:
        options.resize_filter = RESIZE_FILTERS[options.resize_filter]

    creator = ImageCreator(tile_size=options.tile_size,
                           tile_format=options.tile_format,
                           image_quality=options.image_quality,
                           resize_filter=options.resize_filter)
    creator.create(source, options.destination)

if __name__ == '__main__':
    main()
