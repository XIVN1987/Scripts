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
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd

'''
OUTPUT_PYTHON format:

for i2s_philips and msb_justified:
Packet:
[<ptype>, <pdata>]

<ptype>, <pdata>:
 - 'DATA', [<channel>, <value>]

<channel>: 'L' or 'R'
<value>: integer


for pcm_short and pcm_long:
Packet:
[<ptype>, <pdata>]

<ptype>, <pdata>:
 - 'DATA', [<channelL>, <channelR>]

<channelL>: integer
<channelR>: integer
'''

class Decoder(srd.Decoder):
    api_version = 3
    id = 'i2s'
    name = 'I²S'
    longname = 'Integrated Interchip Sound'
    desc = 'Serial bus for connecting digital audio devices.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['i2s']
    tags = ['Audio', 'PC']
    channels = (
        {'id': 'sck', 'name': 'SCK', 'desc': 'Bit clock line'},
        {'id': 'ws',  'name': 'WS',  'desc': 'Word select line'},
        {'id': 'sd',  'name': 'SD',  'desc': 'Serial data line'},
    )
    annotations = (
        ('left', 'Left channel'),
        ('right', 'Right channel'),
        ('warnings', 'Warnings'),
    )
    options = (
        {'id': 'format', 'desc': 'Data format', 'default': 'i2s_philips', 'values': ('i2s_philips', 'msb_justified', 'pcm_short', 'pcm_long')},
    )
    binary = (
        ('wav', 'WAV file'),
    )
    

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.oldws = 1
        self.data = 0
        self.bitcount = 0
        self.wordlength = -1
        self.ss_block = None
        self.wrote_wav_header = False

    def start(self):
        self.out_ann    = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def decode(self):
        while True:
            sck, ws, sd = self.wait({0: 'r'})   # Wait for a rising edge on the SCK pin.

            self.data = (self.data << 1) | sd
            self.bitcount += 1

            #  This was not the LSB unless WS has flipped                                         MSB when WS high
            if self.options['format'] in ('i2s_philips', 'msb_justified') and ws == self.oldws or self.options['format'] in ('pcm_short', 'pcm_long') and ws == 0:
                continue

            # Only submit the sample, if we received the beginning of it.
            if self.ss_block is not None:
                if not self.wrote_wav_header:
                    self.put(0, 0, self.out_binary, [0, self.wav_header()])
                    self.wrote_wav_header = True

                if self.options['format'] in ('i2s_philips', 'msb_justified'):
                    _data     = self.data     if self.options['format'] == 'i2s_philips' else (self.data >> 1)
                    _bitcount = self.bitcount if self.options['format'] == 'i2s_philips' else (self.bitcount - 1)

                    ch = 0              if self.options['format'] == 'i2s_philips' and not self.oldws or self.options['format'] == 'msb_justified' and self.oldws else 1
                    c1 = 'Left channel' if self.options['format'] == 'i2s_philips' and not self.oldws or self.options['format'] == 'msb_justified' and self.oldws else 'Right channel'
                    c2 = 'Left'         if self.options['format'] == 'i2s_philips' and not self.oldws or self.options['format'] == 'msb_justified' and self.oldws else 'Right'
                    c3 = 'L'            if self.options['format'] == 'i2s_philips' and not self.oldws or self.options['format'] == 'msb_justified' and self.oldws else 'R'
                    self.put(self.ss_block, self.samplenum, self.out_ann, [ch, ['%s: %06x' %(c1, _data), '%s: %06x' %(c2, _data), '%s: %06x' %(c3, _data), c3]])
                    #self.put(self.ss_block, self.samplenum, self.out_python, ['DATA', [c3, _data]])
                    #self.put(self.ss_block, self.samplenum, self.out_binary, [0, self.wav_sample(_data)])
                elif self.options['format'] in ('pcm_short', 'pcm_long'):
                    _data     = self.data     if self.options['format'] == 'pcm_short' else (self.data >> 1)
                    _bitcount = self.bitcount if self.options['format'] == 'pcm_short' else (self.bitcount - 1)
                    chbitmask = (1 << (_bitcount // 2)) - 1  # for example: _bitcount = 32, chbitmask = 0xFFFF
                    dataL, dataR = (_data >> (_bitcount // 2)), _data & chbitmask

                    self.put(self.ss_block, self.ss_block + (self.samplenum - self.ss_block)//2,  self.out_ann, [0, ['Left channel: %06x' %dataL, 'Left: %06x' %dataL, 'L: %06x' %dataL, 'L']])
                    self.put(self.ss_block + (self.samplenum - self.ss_block)//2, self.samplenum, self.out_ann, [1, ['Right channel: %06x' %dataR, 'Right: %06x' %dataR, 'R: %06x' %dataR, 'R']])
                    #self.put(self.ss_block, self.samplenum, self.out_python, ['DATA', [dataL, dataR]])
                    #self.put(self.ss_block, self.samplenum, self.out_binary, [0, self.wav_sample(dataL)])
                    #self.put(self.ss_block, self.samplenum, self.out_binary, [0, self.wav_sample(dataR)])

                # Check that the data word was the correct length.
                if self.wordlength != -1 and self.wordlength != _bitcount:
                    self.put(self.ss_block, self.samplenum, self.out_ann, [2, ['Received %d-bit word, expected %d-bit word' % (_bitcount, self.wordlength)]])

                self.wordlength = _bitcount

            # Reset decoder state.
            self.data     = 0 if self.options['format'] in ('i2s_philips', 'pcm_short') else self.data & 1
            self.bitcount = 0 if self.options['format'] in ('i2s_philips', 'pcm_short') else 1
            self.ss_block = self.samplenum

            self.oldws = ws

    def wav_header(self):
        # Chunk descriptor
        h  = b'RIFF'
        h += b'\x24\x80\x00\x00' # Chunk size (2084)
        h += b'WAVE'
        # Fmt subchunk
        h += b'fmt '
        h += b'\x10\x00\x00\x00' # Subchunk size (16 bytes)
        h += b'\x01\x00'         # Audio format (0x0001 == PCM)
        h += b'\x02\x00'         # Number of channels (2)
        h += b'\x80\x3e\x00\x00' # Samplerate (16000)
        h += b'\x00\x7d\x00\x00' # Byterate (32000)
        h += b'\x04\x00'         # Blockalign (4)
        h += b'\x10\x00'         # Bits per sample (16)
        # Data subchunk
        h += b'data'
        h += b'\xff\xff\x00\x00' # Subchunk size (65535 bytes) TODO
        return h

    def wav_sample(self, sample):
        # TODO: This currently assumes U32 samples, and converts to S16.
        s = sample >> 16
        if s >= 0x8000:
            s -= 0x10000
        lo, hi = s & 0xff, (s >> 8) & 0xff
        return bytes([lo, hi])
