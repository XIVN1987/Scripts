#!/usr/bin/python

import os, sys
import threading, time

import socket
from serial import Serial


class UDP2COM(object):
    def __init__(self):
        self.closed = False
        
        self.ser = Serial()
        try:
            self.ser.timeout = 1
            self.ser.xonxoff = 0
            self.ser.port = '/dev/ttyS0'
            self.ser.baudrate = 57600
            self.ser.bytesize = 8
            self.ser.parity = 'N'
            self.ser.stopbits = 1
            self.ser.open()
        except Exception as ex:
            print ex
        else:
            threading.Thread(target=self.ser_recv).start()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind(('192.168.8.1', 8268))
        except Exception as ex:
            print ex
        else:
            threading.Thread(target=self.udp_recv).start()
    
    def ser_recv(self):
        led_state = 0
        while not self.closed:
            n = self.ser.inWaiting()
            if n > 0:
                data = self.ser.read(n)
                if hasattr(self, 'clinAddr'): self.sock.sendto(data, self.clinAddr)
                
                led_state = 1 - led_state
                os.system('echo %d > /sys/class/leds/wrtnode:blue:indicator/brightness' %led_state)
            
            time.sleep(0.1)
        
        self.ser.close()
    
    def udp_recv(self):
        while not self.closed:
            try:
                data, addr = self.sock.recvfrom(1024)
            except Exception as ex:
                pass
            else:
                self.clinAddr = addr
                self.ser.write(data)
                
                if data == 'udp link state': self.sock.sendto('udp link ok', self.clinAddr)
            
            time.sleep(0.1)
        
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        
        try:
            self.sock.close()
        except Exception:
            pass
        
        if hasattr(self, 'clinAddr'):
            delattr(self, 'clinAddr')        


app = UDP2COM()

while 1:
    cmd = raw_input("command: ")
    if cmd == 'stop':
        app.closed = True
        time.sleep(1)
        sys.exit()
