import time
import math
import machine
from machine import Pin


i2c = machine.I2C(0, 400000, sda='PA4', scl='PA5', pullup=False)    # MCP4725 can powered with 5V


class MCP4725(object):
    ''' 12-Bit Digital-to-Analog Converter with EEPROM Memory in SOT-23-6 '''
    def __init__(self, i2c, A0=0):
        super(MCP4725, self).__init__()

        self.i2c  = i2c

        self.addr = 0x62 | A0

        self.offset = 0
        self.k = 1

    def write(self, code):
        buffer = bytearray([int(code) >> 8, int(code) & 0xFF])
        
        self.i2c.writeto(self.addr, buffer)

    def voltage(self, volt):
        ''' volt: in millivolts '''
        code = (volt - self.offset) / self.k
        if code < 0:
            code = 0

        self.write(code)

    def calibrate(self, code_1v, code_3v):
        ''' volt = k * code + offset '''
        self.k = (3000 - 1000) / (code_3v - code_1v)
        self.offset = 3000 - self.k * code_3v

        print('offset = %f mV, k = %f' %(self.offset, self.k))

    def test_sine(self):
        for x in range(1024):
            code = (math.sin((2 * math.pi) * x / 1024) + 1) / 2 * 4095

            self.write(code)


dac = MCP4725(i2c)


pin = machine.Pin('PA2', Pin.OUT)

def test_point(step=20):
    for volt in range(0, 5001, step):
        dac.voltage(volt)
        time.sleep_ms(1)

        pin.high()          # 通知测试板，被测电压已设定，可以测量
        time.sleep_ms(1)
        pin.low()
        time.sleep_ms(10)
