import os
import ctypes
import array
import fcntl

# struct i2c_msg from <linux/i2c.h>
class _CI2CMessage(ctypes.Structure):
    _fields_ = [
        ("addr",  ctypes.c_ushort),
        ("flags", ctypes.c_ushort),
        ("len",   ctypes.c_ushort),
        ("buf",   ctypes.POINTER(ctypes.c_ubyte)),
    ]

# struct i2c_rdwr_ioctl_data from <linux/i2c-dev.h>
class _CI2CIocTransfer(ctypes.Structure):
    _fields_ = [
        ("msgs",  ctypes.POINTER(_CI2CMessage)),
        ("nmsgs", ctypes.c_uint),
    ]

class I2C:
    # Constants from <linux/i2c-dev.h> and <linux/i2c.h>
    _I2C_IOC_FUNCS      = 0x705
    _I2C_IOC_RDWR       = 0x707
    _I2C_FUNC_I2C       = 0x1
    _I2C_M_RD           = 0x0001

    def __init__(self, dev):
        self.dev = dev.lower()

        try:
            self._fd = os.open(self.dev, os.O_RDWR)
        except OSError as e:
            print 'I2C Open Error: ', e.strerror

        # Query supported functions
        buf = array.array('I', [0])
        try:
            fcntl.ioctl(self._fd, I2C._I2C_IOC_FUNCS, buf, True)
        except OSError as e:
            print 'I2C Query Error: ', e.strerror

        if (buf[0] & I2C._I2C_FUNC_I2C) == 0:
            print 'I2C_RDWR ioctl() not supported'

    def xfer(self, address, messages):
        # Convert I2C.Message messages to _CI2CMessage messages
        cmessages = (_CI2CMessage * len(messages))()
        for i in range(len(messages)):
            data = messages[i].data
            cmessages[i].addr = address
            cmessages[i].flags = messages[i].flags | (I2C._I2C_M_RD if messages[i].read else 0)
            cmessages[i].len = len(messages[i].data)
            cmessages[i].buf = ctypes.cast(ctypes.create_string_buffer(data, len(data)), 
                                           ctypes.POINTER(ctypes.c_ubyte))

        i2c_xfer = _CI2CIocTransfer()
        i2c_xfer.nmsgs = len(cmessages)
        i2c_xfer.msgs = cmessages

        try:
            fcntl.ioctl(self._fd, I2C._I2C_IOC_RDWR, i2c_xfer, False)
        except IOError as e:
            print 'I2C Transfer Error: ', e.strerror

        for i in range(len(messages)):
            if messages[i].read:
                data = bytearray([cmessages[i].buf[j] for j in range(cmessages[i].len)])
                messages[i].data = bytes(data)

    def close(self):
        os.close(self._fd)

    def __del__(self):
        self.close()

    def __repr__(self):
        return "I2C('%s')" %self.dev

    class Message:
        def __init__(self, data, read=False, flags=0):
            self.data = data    #type(data) == bytes
            self.read = read
            self.flags = flags