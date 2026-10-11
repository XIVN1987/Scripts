##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2012 Joel Holdsworth <joel@airwebreathe.org.uk>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 2
    id = 'lcd_rgb'
    name = 'LCD RGB'
    desc = 'LCD RGB Interface.'
    inputs = ['logic']
    outputs = ['pixel']
    channels = (
        {'id': 'vsync', 'name': 'VSYNC', 'desc': 'Vertical sync'},
        {'id': 'hsync', 'name': 'HSYNC', 'desc': 'Horizontal sync'},
        {'id': 'dclk',  'name': 'DCLK',  'desc': 'Bit clock line'},
        {'id': 'den',   'name': 'DEN',   'desc': 'Bit data enable'},
        {'id': 'd0',    'name': 'D0',    'desc': 'Data line 0'},
        {'id': 'd1',    'name': 'D1',    'desc': 'Data line 1'},
        {'id': 'd2',    'name': 'D2',    'desc': 'Data line 2'},
        {'id': 'd3',    'name': 'D3',    'desc': 'Data line 3'},
        {'id': 'd4',    'name': 'D4',    'desc': 'Data line 4'},
        {'id': 'd5',    'name': 'D5',    'desc': 'Data line 5'},
        {'id': 'd6',    'name': 'D6',    'desc': 'Data line 6'},
        {'id': 'd7',    'name': 'D7',    'desc': 'Data line 7'},
    )
    annotations = (
        ('data', 'Pixel data'),
        ('sync', 'Sync signal'),
    )
    options = (
        {'id': 'edge',       'desc': 'sample edge',     'default': 'rising', 'values': ('rising', 'falling')},
        {'id': 'endianness', 'desc': 'Data endianness', 'default': 'little', 'values': ('little', 'big')},
    )
    license = 'gplv2+'
    longname = 'LCD RGB Interface'

    def __init__(self):
        self.samplerate = None
        self.ss_block = None
        self.detvsync = False   # 检测到vsync
        self.oldvsync = 1
        self.olddclk = 1
        self.oldden = 0
        self.pixel = 0
        
    def start(self):
        self.out_ann    = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value        

    def decode(self, ss, es, data):
        if not self.samplerate:
            raise Exception('Cannot decode without samplerate.')

        for self.samplenum, (vsync, hsync, dclk, den, *bits) in data:
            data.itercnt += 1
            
            if dclk == self.olddclk:    # Ignore sample if the bit clock hasn't changed.
                continue

            self.olddclk = dclk
            if self.options['edge'] == 'rising'  and dclk == 0:  # Ignore the falling clock edge.
                continue
            if self.options['edge'] == 'falling' and dclk == 1:  # Ignore the rising  clock edge.
                continue

            if self.oldvsync == 1 and vsync == 0:
                self.detvsync = True
            self.oldvsync = vsync

            pixel = 0
            for i, x in enumerate(bits): pixel += (x << i)

            # Only submit the sample, if we received the beginning of it.
            if self.ss_block is not None:
                if self.oldden:
                    self.put(self.ss_block, self.samplenum, self.out_ann, [0, ['%02X' %self.pixel]])

                elif den:
                    if self.detvsync:
                        self.detvsync = False

                        self.put(self.ss_block, self.samplenum, self.out_ann, [1, ['vsync']])
                    else:
                        self.put(self.ss_block, self.samplenum, self.out_ann, [1, ['hsync']])

            # Reset decoder state.
            if self.oldden or den:
                self.ss_block = self.samplenum
            self.oldden = den
            
            self.pixel = pixel
