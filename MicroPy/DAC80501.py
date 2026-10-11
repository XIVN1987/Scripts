import time
import machine
from machine import Pin


i2c = machine.I2C(0, 400000, sda='PA4', scl='PA5', pullup=False)    # DAC80501 can powered with 5V


class DAC80501():
    '''具有精密内部基准的 DAC8/7/60501 16/14/12 位 1LSB INL 电压输出 DAC'''
    DEV_ADDR = 0x90 >> 1

    REG_DEVID = 0x01
    ERG_GAIN  = 0x04
    REG_TRIGR = 0x05
    REG_DATA  = 0x08

    def __init__(self, i2c):
        super(DAC80501, self).__init__()

        self.i2c = i2c

        devid = self.i2c.mem_readfrom(self.DEV_ADDR, self.REG_DEVID, 2)
        print('DEVID = %02X%02Xh' %(devid[0], devid[1]))
    
    def write(self, code):
        self.i2c.mem_writeto(self.DEV_ADDR, self.REG_DATA, bytearray([int(code) >> 8, int(code) & 0xFF]))

    def voltage(self, volt):
        ''' volt: in millivolts '''
        code = volt / 5000 * (2**16 - 1)

        self.write(code)


dac = DAC80501(i2c)

pin = machine.Pin('PA2', Pin.OUT)

def test_point(stop=3300, step=20):
    for volt in range(0, stop+1, step):
        dac.voltage(volt)
        time.sleep_ms(1)

        pin.high()          # 通知测试板，被测电压已设定，可以测量
        time.sleep_ms(1)
        pin.low()
        time.sleep_ms(10)
