class LED:
    def __init__(self, led):
        if led in ['blue_led', 'green_led']:
            self.led = open('/sys/class/leds/%s/brightness' %led, 'w+', buffering=0)
        else:
            raise Exception('led not existed')

    def On(self):
        self.led.write('1')

    def Off(self):
        self.led.write('0')

class PIN:
    pins = ['PA0', 'PA1', 'PA2', 'PA3', 'PA4', 'PA5', 'PA6', 'PA10', 'PA17',
            'PC0', 'PC1', 'PC2', 'PC3', 'PG6', 'PG7', 'PG8', 'PG9',  'PG11']

    def __init__(self, pin, dir):
        pin, dir = pin.upper(), dir.lower()     #dir只能是'in'或'out'
        if pin in self.pins:
            self.num = (ord(pin[1]) - ord('A')) * 32 + int(pin[2:])
            open('/sys/class/gpio/export', 'w', buffering=0).write('%d' %self.num)
            open('/sys/class/gpio/gpio%d/direction' %self.num, 'w', buffering=0).write(dir)
            if dir == 'in':
                self.pin = open('/sys/class/gpio/gpio%d/value' %self.num, 'r')
            elif dir == 'out':
                self.pin = open('/sys/class/gpio/gpio%d/value' %self.num, 'w', buffering=0)
            else:
                raise Exception('dir not valid')
        else:
            raise Exception('pin not existed')

    def Low(self):
        self.pin.write('0')

    def High(self):
        self.pin.write('1')

    def Value(self):
        self.pin.close()
        self.pin = open('/sys/class/gpio/gpio%d/value' %self.num, 'r')
        return int(self.pin.read(1))

    def Close(self):
        open('/sys/class/gpio/unexport', 'w', buffering=0).write('%d' %self.num)


def pinfunc(pin, func=None):
    maps = {'PA0' : ['GPIO_IN', 'GPIO_OUT', 'UART2_TX',  'JTAG_MS', '4', '5', 'PA_EINT0', 'Disable'],
            'PA1' : ['GPIO_IN', 'GPIO_OUT', 'UART2_RX',  'JTAG_CK', '4', '5', 'PA_EINT1', 'Disable'],
            'PA2' : ['GPIO_IN', 'GPIO_OUT', 'UART2_RTS', 'JTAG_DO', '4', '5', 'PA_EINT2', 'Disable'],
            'PA3' : ['GPIO_IN', 'GPIO_OUT', 'UART2_CTS', 'JTAG_DI', '4', '5', 'PA_EINT3', 'Disable'],
            'PA4' : ['GPIO_IN', 'GPIO_OUT', 'UART0_TX',  '3',       '4', '5', 'PA_EINT4', 'Disable'],
            'PA5' : ['GPIO_IN', 'GPIO_OUT', 'UART0_RX',  'PWM0',    '4', '5', 'PA_EINT5', 'Disable'],
            'PA6' : ['GPIO_IN', 'GPIO_OUT', '2',         '3',       '4', '5', 'PA_EINT6', 'Disable'],
            'PA10': ['GPIO_IN', 'GPIO_OUT', '2',         '3',       '4', '5', 'PA_EINT10','Disable'],
            'PA17': ['GPIO_IN', 'GPIO_OUT', 'SPDIF',     '3',       '4', '5', 'PA_EINT17','Disable'],
            'PC0' : ['GPIO_IN', 'GPIO_OUT', '2',       'SPI0_MOSI', '4', '5', '6',        'Disalbe'],
            'PC1' : ['GPIO_IN', 'GPIO_OUT', '2',       'SPI0_MISO', '4', '5', '6',        'Disalbe'],
            'PC2' : ['GPIO_IN', 'GPIO_OUT', '2',       'SPI0_SCLK', '4', '5', '6',        'Disalbe'],
            'PC3' : ['GPIO_IN', 'GPIO_OUT', '2',       'SPI0_SSEL', '4', '5', '6',        'Disalbe'],
            'PG6' : ['GPIO_IN', 'GPIO_OUT', 'UART1_TX',  '3',       '4', '5', 'PG_EINT6', 'Disable'],
            'PG7' : ['GPIO_IN', 'GPIO_OUT', 'UART1_RX',  '3',       '4', '5', 'PG_EINT7', 'Disable'],
            'PG8' : ['GPIO_IN', 'GPIO_OUT', 'UART1_RTS', '3',       '4', '5', 'PG_EINT8', 'Disable'],
            'PG9' : ['GPIO_IN', 'GPIO_OUT', 'UART1_CTS', '3',       '4', '5', 'PG_EINT9', 'Disable'],
            'PG11': ['GPIO_IN', 'GPIO_OUT', '2',         '3',       '4', '5', 'PG_EINT11','Disable'],
    }

    if pin in maps.keys():
        with open('/dev/mem', 'r+b') as f:
            mem = mmap.mmap(f.fileno(), 0x1000, offset=0x01C20000)
            adr = (int(pin[2:]) / 8) * 4 + (ord(pin[1]) - ord('A')) * 0x24 + 0x800
            bit = (int(pin[2:]) % 8) * 4
            reg = struct.unpack('<L', mem[adr:adr+4])[0]
            if func == None:
                return maps[pin][(reg >> bit) & 0x7]
            elif func in maps[pin]:
                val = maps[pin].index(func)
                reg &= ~(0x7 << bit)
                reg |=  (val << bit)
                mem[adr:adr+4] = struct.pack('<L', reg)
            else:
                raise Exception('func not valid')
    else:
        raise Exception('pin not existed')


class PIN:
    pins = ['PA0', 'PA1', 'PA2', 'PA3', 'PA4', 'PA5', 'PA6', 'PA10', 'PA17',
            'PC0', 'PC1', 'PC2', 'PC3', 'PG6', 'PG7', 'PG8', 'PG9',  'PG11']

    def __init__(self, pin, dir):
        pin, dir = pin.upper(), dir.upper()
        if pin in self.pins:
            self.pin = pin
            if dir == 'IN':
                pinfunc(pin, 'GPIO_IN')
            elif dir == 'OUT':
                pinfunc(pin, 'GPIO_OUT')
            else:
                raise Exception('dir not valid')
        else:
            raise Exception('pin not existed')

    def pinreg(self, base, nbit, val=None):
        with open('/dev/mem', 'r+b') as f:
            mem = mmap.mmap(f.fileno(), 0x1000, offset=0x01C20000)
            adr = (int(pin[2:]) / (32 / nbit)) * 4 + (ord(pin[1]) - ord('A')) * 0x24 + base + 0x800
            bit = (int(pin[2:]) % (32 / nbit)) * nbit
            reg = struct.unpack('<L', mem[adr:adr+4])[0]
            if val == None:
                return (reg >> bit) & (2**nbit - 1)
            elif nbit == 1:
                if val == 0: reg &= ~(1 << bit)
                else:        reg |=  (1 << bit)
            else:
                reg &= ~((2**nbit - 1) << bit)
                reg |=  (val           << bit)
            mem[adr:adr+4] = struct.pack('<L', reg)

    def Low(self):
        self.pinreg(0x10, 1, 0)

    def High(self):
        self.pinreg(0x10, 1, 1)

    def Value(self):
        return self.pinreg(0x10, 1)

    def Pull(self, val=None):
        if val == None:
            return ('Disable', 'Up', 'Down')[self.pinreg(0x1C, 2)]
        elif val == 'Up':
            self.pinreg(0x1C, 2, 1)
        elif val == 'Down':
            self.pinreg(0x1C, 2, 2)
        else:
            self.pinreg(0x1C, 2, 0)