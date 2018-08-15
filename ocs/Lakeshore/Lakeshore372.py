# Lakeshore372.py
# 6/6/2018
# Lauren Saunders
# Follows similar commands to Lakeshore240.py

import serial
import socket
import time
from ocs.Lakeshore.channel372 import Channel372

class LS372:
    """
        Lakeshore 372 class.
    """
    def __init__(self, ip, baud=57600, timeout=10, num_channels=16):
        self.com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.com.connect((ip, 7777))
        self.com.settimeout(timeout)
        self.num_channels = num_channels
         
        self.id = self.test()
        #Enable all channels
        # going to hold off on enabling all channels automatically - bjk
        #for i in range(self.num_channels):
        #    print(i)
        #    self.msg('INSET %d,1,3,3'%(i))

        self.channels = []
        for i in range(num_channels):
            c = Channel372(self, i+1)
            self.channels.append(c)

    def msg(self, message):
        msg_str = f'{message}\r\n'.encode()
        self.com.send(msg_str)
        if '?' in message:
            time.sleep(0.01)
            resp = str(self.com.recv(4096)[:-2], 'utf-8')
        else:
            resp = ''
        return resp

    def test(self):
        return self.msg('*IDN?')
    
    def set_autoscan(self, start=1, autoscan=0):
        self.msg('SCAN {},{}'.format(start, autoscan))

    def get_temp(self, unit="S", chan=-1):
        
        if (chan==-1):
            resp = self.msg("SCAN?")
            c = resp.split(',')[0]
        elif (chan==0):
            c = 'A'
        else:
            c=str(chan)
        
        if unit == 'S':
            # Sensor is same as Resistance Query
            return float(self.msg('SRDG? %s'%c))
        if unit == 'K':
            return float(self.msg('KRDG? %s'%c))

if __name__=="__main__":
    import json
    with open("ips.json") as file:
        ips = json.load(file)
    name="LS372A"
    ls = LS372(ips[name])

