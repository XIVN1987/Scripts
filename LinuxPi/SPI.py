import os
import fcntl
import array
import ctypes

# struct spi_ioc_transfer from <linux/spi/spidev.h>
class _CSpiIocTransfer(ctypes.Structure):
    _fields_ = [
        ('tx_buf',        ctypes.c_ulonglong),
        ('rx_buf',        ctypes.c_ulonglong),
        ('len',           ctypes.c_uint),
        ('speed_hz',      ctypes.c_uint),
        ('delay_usecs',   ctypes.c_ushort),
        ('bits_per_word', ctypes.c_ubyte),
        ('cs_change',     ctypes.c_ubyte),
        ('tx_nbits',      ctypes.c_ubyte),
        ('rx_nbits',      ctypes.c_ubyte),
        ('pad',           ctypes.c_ushort),
    ]

class SPI:
    # Constants from <linux/spi/spidev.h>
    _SPI_CPHA        = 0x1
    _SPI_CPOL        = 0x2
    _SPI_LSB_FIRST   = 0x8
    _SPI_IOC_WR_MODE            = 0x40016b01
    _SPI_IOC_RD_MODE            = 0x80016b01
    _SPI_IOC_WR_MAX_SPEED_HZ    = 0x40046b04
    _SPI_IOC_RD_MAX_SPEED_HZ    = 0x80046b04
    _SPI_IOC_WR_BITS_PER_WORD   = 0x40016b03
    _SPI_IOC_RD_BITS_PER_WORD   = 0x80016b03
    _SPI_IOC_MESSAGE_1          = 0x40206b00

    def __init__(self, dev, mode, max_speed, bit_order="MSB", bits_per_word=8):
        self.dev, self.mode, self.max_speed, self.bit_order, self.bits_per_word = \
             dev, mode, self.MKToInt(max_speed), bit_order.upper(), bits_per_word

        try:
            self._fd = os.open(dev, os.O_RDWR)
        except OSError as e:
            print 'SPI Open Error: ', e.strerror
        
        buf = array.array("B", [self.mode | (self._SPI_LSB_FIRST if bit_order=="LSB" else 0)])
        fcntl.ioctl(self._fd, self._SPI_IOC_WR_MODE, buf, False)

        buf = array.array("I", [self.max_speed])
        fcntl.ioctl(self._fd, self._SPI_IOC_WR_MAX_SPEED_HZ, buf, False)

        buf = array.array("B", [self.bits_per_word])
        fcntl.ioctl(self._fd, self._SPI_IOC_WR_BITS_PER_WORD, buf, False)

    def xfer(self, data):
        buf = array.array('B', data)
        buf_addr, buf_len = buf.buffer_info()

        spi_xfer = _CSpiIocTransfer()
        spi_xfer.tx_buf = buf_addr
        spi_xfer.rx_buf = buf_addr
        spi_xfer.len    = buf_len

        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_MESSAGE_1, spi_xfer)
        except OSError as e:
            print 'SPI Transfer Error: ', e.strerror

        return buf.tolist()

    def close(self):
        os.close(self._fd)

    def __del__(self):
        self.close()

    def __repr__(self):
        return "SPI('%s', %d, '%s', bit_order='%s', bits_per_word=%d)" %(self.dev, self.mode,
                  self.IntToMK(self.max_speed), self.bit_order, self.bits_per_word)

    def MKToInt(self, val):
        return int(val[:-1]) * {'M': 1000000, 'K': 1000}[val[-1].upper()]

    def IntToMK(self, val):
        return '%dM' %(val/1000000) if val >= 1000000 else '%dK' %(val/1000)