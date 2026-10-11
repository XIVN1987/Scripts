import sigrokdecode as srd


class Decoder(srd.Decoder):
    api_version = 3
    id = 'canfd'
    name = 'CANFD'
    longname = 'Controller Area Network with Flexible Data-Rate'
    desc = 'Field bus protocol for distributed realtime control.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Automotive']
    channels = (
        {'id': 'can_rx', 'name': 'CAN', 'desc': 'CAN bus line'},
    )
    options = (
        {'id': 'bitrate', 'desc': 'Bitrate (bits/s)', 'default': 100000},
        {'id': 'sample_point', 'desc': 'Sample point (%)', 'default': 70.0},
        {'id': 'data_bitrate', 'desc': 'Data Bitrate (bits/s)', 'default': 500000},
        {'id': 'data_sample_point', 'desc': 'Data Sample point (%)', 'default': 70.0},
    )
    annotations = (
        ('data', 'CAN payload data'),
        ('sof', 'Start of frame'),
        ('eof', 'End of frame'),
        ('id', 'Identifier'),
        ('ext-id', 'Extended identifier'),
        ('full-id', 'Full identifier'),
        ('ide', 'Identifier extension bit'),
        ('reserved-bit', 'Reserved bit 0 and 1'),
        ('rtr', 'Remote transmission request'),
        ('srr', 'Substitute remote request'),
        ('fdf', 'Flexible Data-Rate Format'),
        ('brs', 'Bit Rate Switch'),
        ('esi', 'Error Status Indicator'),
        ('dlc', 'Data length count'),
        ('sbc', 'Stuff Bit Count'),
        ('crc-sequence', 'CRC sequence'),
        ('crc-delimiter', 'CRC delimiter'),
        ('ack-slot', 'ACK slot'),
        ('ack-delimiter', 'ACK delimiter'),
        ('stuff-bit', 'Stuff bit'),
        ('warnings', 'Human-readable warnings'),
        ('bit', 'Bit'),
    )
    bit_data =  0
    bit_sof  =  1
    bit_eof  =  2
    bit_id   =  3
    bit_eid  =  4
    bit_fid  =  5
    bit_ide  =  6
    bit_rsv  =  7
    bit_rtr  =  8
    bit_srr  =  9
    bit_fdf  = 10
    bit_brs  = 11
    bit_esi  = 12
    bit_dlc  = 13
    bit_sbc  = 14
    bit_crc  = 15
    bit_crcd = 16
    bit_ack  = 17
    bit_ackd = 18
    bit_stuf = 19
    bit_warn = 20
    bit_bit  = 21

    annotation_rows = (
        ('bits', 'Bits', (bit_stuf, bit_bit)),
        ('fields', 'Fields', tuple(range(bit_stuf))),
        ('warnings', 'Warnings', (bit_warn,)),
    )


    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.reset_variables()

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value
            self.bit_width = float(self.samplerate) / float(self.options['bitrate'])
            self.sample_point = (self.bit_width / 100.0) * self.options['sample_point']

    # Generic helper for CAN bit annotations.
    def putg(self, ss, es, data):
        self.put(ss - int(self.sample_point), es + int(self.bit_width - self.sample_point), self.out_ann, data)

    # Single-CAN-bit annotation using the current samplenum.
    def putx(self, data):
        self.putg(self.samplenum, self.samplenum, data)

    # Multi-CAN-bit annotation from self.ss_block to current samplenum.
    def putb(self, data):
        self.putg(self.ss_block, self.samplenum, data)

    def reset_variables(self):
        self.state = 'IDLE'
        self.frame_type = None
        self.rawbits  = []          # All bits, including stuff bits
        self.bits     = []          # Only CAN frame bits (no stuff bits)
        self.databitn = []          # bitnum of CAN frame payload bits
        self.rawbitnum = 0          # SOF's rawbitnum is 0
        self.datanbyte = None       # CAN frame payload number of byte
        self.lastdb_bitnum = 999    # bitnum of last data bit
        self.lastdb_rawbitnum = 999
        self.ss_block = None
        self.ss_bit12 = None
        self.ss_bit32 = None

    
    # Both standard and extended frames end with CRC, CRC delimiter, ACK, ACK delimiter, and EOF fields.
    # Returns True if the frame ended (EOF), False otherwise.
    def decode_frame_end(self, can_rx, bitnum):

        # Remember start of CRC sequence (see below).
        if bitnum == (self.lastdb_bitnum + 1):
            self.ss_block = self.samplenum

        # CRC sequence (15 bits)
        elif bitnum == (self.lastdb_bitnum + 15):
            x = self.lastdb_bitnum + 1
            crc_bits = self.bits[x:x + 15 + 1]
            self.crc = int(''.join(str(d) for d in crc_bits), 2)
            self.putb([self.bit_crc, [f'CRC sequence: 0x{self.crc:04x}', f'CRC: 0x{self.crc:04x}', 'CRC']])

        # CRC delimiter bit (recessive)
        elif bitnum == (self.lastdb_bitnum + 16):
            self.putx([self.bit_crcd, [f'CRC delimiter: {can_rx}', f'CRC d: {can_rx}', 'CRC d']])
            if can_rx != 1:
                self.putx([self.bit_warn, ['CRC delimiter must be a recessive bit']])

        # ACK slot bit (dominant: ACK, recessive: NACK)
        elif bitnum == (self.lastdb_bitnum + 17):
            ack = 'ACK' if can_rx == 0 else 'NACK'
            self.putx([self.bit_ack, [f'ACK slot: {ack}', f'ACK s: {ack}', 'ACK s']])

        # ACK delimiter bit (recessive)
        elif bitnum == (self.lastdb_bitnum + 18):
            self.putx([self.bit_ackd, [f'ACK delimiter: {can_rx}', f'ACK d: {can_rx}', 'ACK d']])
            if can_rx != 1:
                self.putx([self.bit_warn, ['ACK delimiter must be a recessive bit']])

        # Remember start of EOF (see below).
        elif bitnum == (self.lastdb_bitnum + 19):
            self.ss_block = self.samplenum

        # End of frame (EOF), 7 recessive bits
        elif bitnum == (self.lastdb_bitnum + 25):
            self.putb([self.bit_eof, ['End of frame', 'EOF', 'E']])
            if self.rawbits[-7:] != [1, 1, 1, 1, 1, 1, 1]:
                self.putb([self.bit_warn, ['End of frame (EOF) must be 7 recessive bits']])

            self.reset_variables()

            return True

        return False

    def decode_fdframe_end(self, can_rx, bitnum):

        # Remember start of SBC (see below).
        if bitnum == (self.lastdb_bitnum + 1):
            self.ss_block = self.samplenum

        # Stuff Bit Count (4 bits)
        elif bitnum == (self.lastdb_bitnum + 4):
            x = self.lastdb_bitnum + 1
            sbc_bits = ''.join(str(d) for d in self.bits[x:x + 3])
            if   sbc_bits == '000': self.sbc = 0
            elif sbc_bits == '001': self.sbc = 1
            elif sbc_bits == '011': self.sbc = 2
            elif sbc_bits == '010': self.sbc = 3
            elif sbc_bits == '110': self.sbc = 4
            elif sbc_bits == '111': self.sbc = 5
            elif sbc_bits == '101': self.sbc = 6
            elif sbc_bits == '100': self.sbc = 7
            self.putb([self.bit_crc, [f'Stuff Bit Count: {self.sbc}', f'SBC: {self.sbc}', 'SBC']])

        # Remember start of CRC sequence (see below).
        if bitnum == (self.lastdb_bitnum + 5):
            self.ss_block = self.samplenum

        # CRC sequence (17 or 21 bits)
        elif bitnum == (self.lastdb_bitnum + 5 + self.crc_nbit - 1):
            x = self.lastdb_bitnum + 1
            crc_bits = self.bits[x:x + self.crc_nbit + 1]
            self.crc = int(''.join(str(d) for d in crc_bits), 2)
            self.putb([self.bit_crc, [f'CRC sequence: 0x{self.crc:06x}', f'CRC: 0x{self.crc:06x}', 'CRC']])

        # CRC delimiter bit (recessive)
        elif bitnum == (self.lastdb_bitnum + self.crc_nbit + 5):
            self.putx([self.bit_crcd, [f'CRC delimiter: {can_rx}', f'CRC d: {can_rx}', 'CRC d']])
            if can_rx != 1:
                self.putx([self.bit_warn, ['CRC delimiter must be a recessive bit']])

        # ACK slot bit (dominant: ACK, recessive: NACK)
        elif bitnum == (self.lastdb_bitnum + self.crc_nbit + 6):
            ack = 'ACK' if can_rx == 0 else 'NACK'
            self.putx([self.bit_ack, [f'ACK slot: {ack}', f'ACK s: {ack}', 'ACK s']])

        # ACK delimiter bit (recessive)
        elif bitnum == (self.lastdb_bitnum + self.crc_nbit + 7):
            self.putx([self.bit_ackd, [f'ACK delimiter: {can_rx}', f'ACK d: {can_rx}', 'ACK d']])
            if can_rx != 1:
                self.putx([self.bit_warn, ['ACK delimiter must be a recessive bit']])

        # Remember start of EOF (see below).
        elif bitnum == (self.lastdb_bitnum + self.crc_nbit + 8):
            self.ss_block = self.samplenum

        # End of frame (EOF), 7 recessive bits
        elif bitnum == (self.lastdb_bitnum + self.crc_nbit + 14):
            self.putb([self.bit_eof, ['End of frame', 'EOF', 'E']])
            if self.rawbits[-7:] != [1, 1, 1, 1, 1, 1, 1]:
                self.putb([self.bit_warn, ['End of frame (EOF) must be 7 recessive bits']])

            self.reset_variables()

            return True

        return False

    # Returns True if the frame ended (EOF), False otherwise.
    def decode_standard_frame(self, can_rx, bitnum):

        # Bit 14: FDF (Flexible Data-Rate Format)
        if bitnum == 14:
            self.putx([self.bit_fdf, [f'Flexible Data-Rate Format: {can_rx}', f'FDF: {can_rx}', 'FDF']])

            if can_rx == 0:
                # Bit 12: Remote transmission request (RTR) bit
                rtr = 'remote' if self.bits[12] == 1 else 'data'
                self.putg(self.ss_bit12, self.ss_bit12, [self.bit_rtr, [f'Remote transmission request: {rtr} frame', f'RTR: {rtr} frame', 'RTR']])

            else:
                self.frame_type = 'standard fd'

                # Bit 12: Substitute remote request (SRR) bit
                self.putg(self.ss_bit12, self.ss_bit12, [self.bit_srr, [f'Substitute remote request: {self.bits[12]}', f'SRR: {self.bits[12]}', 'SRR']])

        # Remember start of DLC (see below).
        elif bitnum == 15:
            self.ss_block = self.samplenum

        # Bits 15-18: Data length code (DLC), in number of bytes (0-8).
        elif bitnum == 18:
            self.datanbyte = int(''.join(str(d) for d in self.bits[15:18 + 1]), 2)
            self.putb([self.bit_dlc, [f'Data length code: {self.datanbyte}', f'DLC: {self.datanbyte}', 'DLC']])
            self.lastdb_bitnum = 18 + (self.datanbyte * 8)
            if self.datanbyte > 8:
                self.putb([self.bit_warn, ['Data length code (DLC) > 8 is not allowed']])

        # Remember all databyte bits, except the very last one.
        elif bitnum in range(19, self.lastdb_bitnum):
            self.databitn.append(self.samplenum)

        # Bits 19-X: Data field (0-8 bytes, depending on DLC)
        # The bits within a data byte are transferred MSB-first.
        elif bitnum == self.lastdb_bitnum:
            self.databitn.append(self.samplenum) # Last databyte bit.
            for i in range(self.datanbyte):
                x = 18 + (8 * i) + 1
                b = int(''.join(str(d) for d in self.bits[x:x + 8]), 2)
                ss = self.databitn[i * 8]
                es = self.databitn[((i + 1) * 8) - 1]
                self.putg(ss, es, [self.bit_data, [f'Data byte {i}: 0x{b:02x}', f'DB {i}: 0x{b:02x}', 'DB']])
            self.databitn = []

        elif bitnum > self.lastdb_bitnum:
            return self.decode_frame_end(can_rx, bitnum)

        return False

    def decode_extended_frame(self, can_rx, bitnum):

        # Remember start of EID (see below).
        if bitnum == 14:
            self.ss_block = self.samplenum

        # Bits 14-31: Extended identifier (EID[17..0])
        elif bitnum == 31:
            self.eid = int(''.join(str(d) for d in self.bits[14:]), 2)
            s = f'{self.eid} (0x{self.eid:x})'
            self.putb([self.bit_eid, [f'Extended Identifier: {s}', f'Extended ID: {s}', 'Extended ID', 'EID']])

            self.fullid = self.id << 18 | self.eid
            s = f'{self.fullid} (0x{self.fullid:x})'
            self.putb([self.bit_fid, [f'Full Identifier: {s}', f'Full ID: {s}', 'Full ID', 'FID']])

            # Bit 12: Substitute remote request (SRR) bit
            self.putg(self.ss_bit12, self.ss_bit12, [self.bit_srr, [f'Substitute remote request: {self.bits[12]}', f'SRR: {self.bits[12]}', 'SRR']])

        # RTR or SRR bit, depending on frame type (gets handled later).
        if bitnum == 32:
            self.ss_bit32 = self.samplenum

        # Bit 33: FDF (Flexible Data-Rate Format)
        elif bitnum == 33:
            self.putx([self.bit_fdf, [f'Flexible Data-Rate Format: {can_rx}', f'FDF: {can_rx}', 'FDF']])
            
            if can_rx == 0:
                # Bit 32: Remote transmission request (RTR) bit
                rtr = 'remote' if self.bits[32] == 1 else 'data'
                self.putg(self.ss_bit32, self.ss_bit32, [self.bit_rtr, [f'Remote transmission request: {rtr} frame', f'RTR: {rtr} frame', 'RTR']])

            else:
                self.frame_type = 'extended fd'

                # Bit 32: Substitute remote request (SRR) bit
                self.putg(self.ss_bit32, self.ss_bit32, [self.bit_srr, [f'Substitute remote request: {self.bits[32]}', f'SRR: {self.bits[32]}', 'SRR']])

        # Bit 34: RB0 (reserved bit)
        elif bitnum == 34:
            self.putx([self.bit_rsv, [f'Reserved bit 0: {can_rx}', f'RB0: {can_rx}', 'RB0']])

        # Remember start of DLC (see below).
        elif bitnum == 35:
            self.ss_block = self.samplenum

        # Bits 35-38: Data length code (DLC), in number of bytes (0-8).
        elif bitnum == 38:
            self.datanbyte = int(''.join(str(d) for d in self.bits[35:38 + 1]), 2)
            self.putb([self.bit_dlc, [f'Data length code: {self.datanbyte}', f'DLC: {self.datanbyte}', 'DLC']])
            self.lastdb_bitnum = 38 + (self.datanbyte * 8)
            if self.datanbyte > 8:
                self.putb([self.bit_warn, ['Data length code (DLC) > 8 is not allowed']])

        # Remember all databyte bits, except the very last one.
        elif bitnum in range(39, self.lastdb_bitnum):
            self.databitn.append(self.samplenum)

        # Bits 39-X: Data field (0-8 bytes, depending on DLC)
        # The bits within a data byte are transferred MSB-first.
        elif bitnum == self.lastdb_bitnum:
            self.databitn.append(self.samplenum) # Last databyte bit.
            for i in range(self.datanbyte):
                x = 38 + (8 * i) + 1
                b = int(''.join(str(d) for d in self.bits[x:x + 8]), 2)
                ss = self.databitn[i * 8]
                es = self.databitn[((i + 1) * 8) - 1]
                self.putg(ss, es, [self.bit_data, [f'Data byte {i}: 0x{b:02x}', f'DB {i}: 0x{b:02x}', 'DB']])
            self.databitn = []

        elif bitnum > self.lastdb_bitnum:
            return self.decode_frame_end(can_rx, bitnum)

        return False

    def decode_standard_fdframe(self, can_rx, bitnum):

        # Bit 15: RB0 (reserved bit)
        # Has to be sent dominant, but receivers should accept recessive too.
        if bitnum == 15:
            self.putx([self.bit_rsv, [f'Reserved bit 0: {can_rx}', f'RB0: {can_rx}', 'RB0']])

        # Bit 16: BRS (Bit Rate Switch)
        elif bitnum == 16:
            self.putx([self.bit_brs, [f'Bit Rate Switch: {can_rx}', f'BRS: {can_rx}', 'BRS']])

        # Bit 17: ESI (Error Status Indicator)
        elif bitnum == 17:
            self.putx([self.bit_esi, [f'Error Status Indicator: {can_rx}', f'ESI: {can_rx}', 'ESI']])

        # Remember start of DLC (see below).
        elif bitnum == 18:
            self.ss_block = self.samplenum

        # Bits 18-21: Data length code (DLC), in number of bytes (0-8).
        elif bitnum == 21:
            self.datanbyte = int(''.join(str(d) for d in self.bits[18:21 + 1]), 2)
            if   self.datanbyte ==  9: self.datanbyte = 12
            elif self.datanbyte == 10: self.datanbyte = 16
            elif self.datanbyte == 11: self.datanbyte = 20
            elif self.datanbyte == 12: self.datanbyte = 24
            elif self.datanbyte == 13: self.datanbyte = 32
            elif self.datanbyte == 14: self.datanbyte = 48
            elif self.datanbyte == 15: self.datanbyte = 64
            self.putb([self.bit_dlc, [f'Data length code: {self.datanbyte}', f'DLC: {self.datanbyte}', 'DLC']])

            self.lastdb_bitnum = 21 + (self.datanbyte * 8)

            self.crc_nbit = 17 if self.datanbyte < 20 else 21

        # Remember all databyte bits, except the very last one.
        elif bitnum in range(22, self.lastdb_bitnum):
            self.databitn.append(self.samplenum)

        # Bits 22-X: Data field (0-8 bytes, depending on DLC)
        # The bits within a data byte are transferred MSB-first.
        elif bitnum == self.lastdb_bitnum:
            self.databitn.append(self.samplenum) # Last databyte bit.
            for i in range(self.datanbyte):
                x = 21 + (8 * i) + 1
                b = int(''.join(str(d) for d in self.bits[x:x + 8]), 2)
                ss = self.databitn[i * 8]
                es = self.databitn[((i + 1) * 8) - 1]
                self.putg(ss, es, [self.bit_data, [f'Data byte {i}: 0x{b:02x}', f'DB {i}: 0x{b:02x}', 'DB']])
            self.databitn = []

            self.lastdb_rawbitnum = self.rawbitnum

        elif bitnum > self.lastdb_bitnum:
            return self.decode_fdframe_end(can_rx, bitnum)

        return False

    def decode_extended_fdframe(self, can_rx, bitnum):

        # Bit 34: RB0 (reserved bit)
        if bitnum == 34:
            self.putx([self.bit_rsv, [f'Reserved bit 0: {can_rx}', f'RB0: {can_rx}', 'RB0']])

        # Bit 35: BRS (Bit Rate Switch)
        elif bitnum == 35:
            self.putx([self.bit_brs, [f'Bit Rate Switch: {can_rx}', f'BRS: {can_rx}', 'BRS']])

        # Bit 36: ESI (Error Status Indicator)
        elif bitnum == 36:
            self.putx([self.bit_esi, [f'Error Status Indicator: {can_rx}', f'ESI: {can_rx}', 'ESI']])

        # Remember start of DLC (see below).
        elif bitnum == 37:
            self.ss_block = self.samplenum

        # Bits 37-40: Data length code (DLC), in number of bytes (0-8).
        elif bitnum == 40:
            self.datanbyte = int(''.join(str(d) for d in self.bits[37:40 + 1]), 2)
            if   self.datanbyte ==  9: self.datanbyte = 12
            elif self.datanbyte == 10: self.datanbyte = 16
            elif self.datanbyte == 11: self.datanbyte = 20
            elif self.datanbyte == 12: self.datanbyte = 24
            elif self.datanbyte == 13: self.datanbyte = 32
            elif self.datanbyte == 14: self.datanbyte = 48
            elif self.datanbyte == 15: self.datanbyte = 64
            self.putb([self.bit_dlc, [f'Data length code: {self.datanbyte}', f'DLC: {self.datanbyte}', 'DLC']])

            self.lastdb_bitnum = 40 + (self.datanbyte * 8)

            self.crc_nbit = 17 if self.datanbyte < 20 else 21

        # Remember all databyte bits, except the very last one.
        elif bitnum in range(41, self.lastdb_bitnum):
            self.databitn.append(self.samplenum)

        # Bits 41-X: Data field (0-8 bytes, depending on DLC)
        # The bits within a data byte are transferred MSB-first.
        elif bitnum == self.lastdb_bitnum:
            self.databitn.append(self.samplenum) # Last databyte bit.
            for i in range(self.datanbyte):
                x = 40 + (8 * i) + 1
                b = int(''.join(str(d) for d in self.bits[x:x + 8]), 2)
                ss = self.databitn[i * 8]
                es = self.databitn[((i + 1) * 8) - 1]
                self.putg(ss, es, [self.bit_data, [f'Data byte {i}: 0x{b:02x}', f'DB {i}: 0x{b:02x}', 'DB']])
            self.databitn = []

            self.lastdb_rawbitnum = self.rawbitnum

        elif bitnum > self.lastdb_bitnum:
            return self.decode_fdframe_end(can_rx, bitnum)

        return False


    def is_stuff_bit(self, bitnum):
        if self.datanbyte is not None and self.frame_type.endswith('fd'):
            if self.lastdb_bitnum < bitnum <= self.lastdb_bitnum + 4 + self.crc_nbit:
                if (self.rawbitnum - self.lastdb_rawbitnum) % 5 == 1:
                    return True
                else:
                    return False
        
        # After 5 identical bits, a stuff bit of opposite value is added.
        # But not in the CRC delimiter, ACK, and end of frame fields.
        if bitnum > self.lastdb_bitnum + 15:
            return False

        if self.rawbits[-6:] in ([0, 0, 0, 0, 0, 1], [1, 1, 1, 1, 1, 0]):
            return True
        
        return False

    def handle_bit(self, can_rx):
        self.rawbits.append(can_rx)
        self.bits.append(can_rx)

        # Get the index of the current CAN frame bit (without stuff bits).
        bitnum = len(self.bits) - 1

        # If this is a stuff bit, remove it from self.bits and ignore it.
        if self.is_stuff_bit(bitnum):
            self.bits.pop()

            self.putx([self.bit_stuf, [str(can_rx)]])
            self.rawbitnum += 1
            return

        else:
            self.putx([self.bit_bit, [str(can_rx)]])

        # Bit 0: Start of frame (SOF) bit
        if bitnum == 0:
            self.putx([self.bit_sof, ['Start of frame', 'SOF', 'S']])
            if can_rx != 0:
                self.putx([self.bit_warn, ['Start of frame (SOF) must be a dominant bit']])

        # Remember start of ID (see below).
        elif bitnum == 1:
            self.ss_block = self.samplenum

        # Bits 1-11: Identifier (ID[10..0])
        # The bits ID[10..4] must NOT be all recessive.
        elif bitnum == 11:
            self.id = int(''.join(str(d) for d in self.bits[1:]), 2)
            s = f'{self.id} (0x{self.id:x})'
            self.putb([self.bit_id, [f'Identifier: {s}', f'ID: {s}', 'ID']])
            if (self.id & 0x7f0) == 0x7f0:
                self.putb([self.bit_warn, ['Identifier bits 10..4 must not be all recessive']])

        # RTR or SRR bit, depending on frame type (gets handled later).
        elif bitnum == 12:
            self.ss_bit12 = self.samplenum

        # Bit 13: Identifier extension (IDE) bit
        # Standard frame: dominant, extended frame: recessive
        elif bitnum == 13:
            ide = self.frame_type = 'standard' if can_rx == 0 else 'extended'
            self.putx([self.bit_ide, [f'Identifier extension bit: {ide} frame', f'IDE: {ide} frame', 'IDE']])

        # Bits 14-X: Frame-type dependent, passed to the resp. handlers.
        elif bitnum >= 14:
            if self.frame_type == 'standard':
                done = self.decode_standard_frame(can_rx, bitnum)
            elif self.frame_type == 'extended':
                done = self.decode_extended_frame(can_rx, bitnum)
            elif self.frame_type == 'standard fd':
                done = self.decode_standard_fdframe(can_rx, bitnum)
            else:
                done = self.decode_extended_fdframe(can_rx, bitnum)

            # The handlers return True if a frame ended (EOF).
            if done:
                return

        # After a frame there are 3 intermission bits (recessive).
        # After these bits, the bus is considered free.

        self.rawbitnum += 1

    # Poor man's clock synchronization. Use signal edges which change to dominant state in rather simple ways.
    # This naive approach is neither aware of the SYNC phase's width nor the specific location of the edge,
    # but improves the decoder's reliability when the input signal's bitrate does not exactly match the nominal rate.
    def edge_seen(self):
        self.edge_samplenum = self.samplenum
        self.edge_rawbitnum = self.rawbitnum

    def decode(self):
        while True:
            if self.state == 'IDLE':
                # Wait for a dominant state (logic 0) on the bus.
                (can_rx,) = self.wait({0: 'l'})
                self.edge_seen()
                self.state = 'FRAME'

            else:
                # Wait until we're in the correct bit/sampling position.
                sample_point = self.edge_samplenum + int(self.bit_width * (self.rawbitnum - self.edge_rawbitnum)) + int(self.sample_point)
                (can_rx,) = self.wait([{'skip': sample_point - self.samplenum}, {0: 'f'}])
                if self.matched & (1 << 1):
                    self.edge_seen()
                if self.matched & (1 << 0):
                    self.handle_bit(can_rx)
