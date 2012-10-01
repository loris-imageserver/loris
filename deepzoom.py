#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  NOTE THAT THIS IS NOT THE FULL deepzoom.py MODULE. It only includes a 
#  modified version if that module's DeepZoomImageDescriptor class thus
#  eliminating loris's dependency on the PIL. The original module may be found 
#  at <https://github.com/openzoom/deepzoom.py>
#
#  Original license statement follows:
#  """
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
import xml.dom.minidom

NS_DEEPZOOM = 'http://schemas.microsoft.com/deepzoom/2008'

class DeepZoomImageDescriptor(object):
    def __init__(self, width=None, height=None,
                 tile_size=256, tile_overlap=0, tile_format='jpg'):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.tile_format = tile_format
        self._num_levels = None

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
