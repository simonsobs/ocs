#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 14:15:51 2018

@author: jacoblashner
"""

from serial import Serial
from serial.serialutil import SerialException
import time
from ocs.Lakeshore.Channel import Channel
import sys

try:
    from tqdm import *
except ModuleNotFoundError:
    tqdm = lambda x: x


class Module:
    """
        Allows communication to Lakeshore Module.
        Contains list of inputs which can be read from.
    """
    
    def __init__(self, port='/dev/tty.SLAB_USBtoUART', baud=115200, timeout=10, num_channels=2):
        """
            Establish Serial communication and initialize channels.
        """
        self.com = Serial(port=port, baudrate=baud, timeout=timeout)
        self.idn = self.test()

        self.channels = []
        for i in range(num_channels):
            c = Channel(self, i+1, enabled=True)
            c.name = f'Input {i+1}'
            c.update_info()
            self.channels.append(c)

    def open_com(self):
        try:
            self.com.open()
        except SerialException:
            print("Port already open")

    def close_com(self):
        self.com.close()

    def msg(self, msg):
        """
            Send command or query to module. 
            Return response (within timeout) if message is a query.
        """
        # Writes message
        message_string = f'{msg}\r\n;'.encode()

        # write(message_string)
        self.com.write(message_string)

        # Reads response if queried
        resp = ''
        if "?" in msg:
            resp = self.com.readline()
            resp = str(resp[:-2], 'utf-8')       # Strips terminating chars
            if not resp:
                raise TimeoutError("Device timed out")

            time.sleep(.01)             # Must wait 10 ms before sending another command

        return resp
    
    def test(self):
        """ Return IDN of module. """
        return self.msg("*IDN?")

    def __repr__(self):
        return f"Lakeshore240"

    def __str__(self):
        string = f"ID: {self.idn}\n"
        #for c in self.channels:
        #    string += str(c)
        return string
        

if __name__ == "__main__":
    ls = Module(port="/dev/ttyUSB0")
    print (ls)
    
 
