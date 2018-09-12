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
    
    def __init__(self, port='/dev/tty.SLAB_USBtoUART', baud=115200, timeout=10):
        """
            Establish Serial communication and initialize channels.
        """
        self.com = Serial(port=port, baudrate=baud, timeout=timeout)

        idn = self.msg("*IDN?")
        self.manufacturer, self.model, self.inst_sn, self.firmware_version = idn.split(',')
        num_channels = int(self.model[-2])

        self.name = self.msg("MODNAME?")

        self.channels = []
        for i in range(num_channels):
            c = Channel(self, i+1)
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
        message_string = "{}\r\n;".format(msg).encode()

        # write(message_string)
        self.com.write(message_string)

        # Reads response if queried
        resp = ''
        if "?" in msg:
            resp = self.com.readline()
            resp = str(resp[:-2], 'utf-8')       # Strips terminating chars
            if not resp:
                raise TimeoutError("Device timed out")

            # time.sleep(.01)             # Must wait 10 ms before sending another command

        return resp

    def set_name(self, name):
        self.name = name
        self.msg("MODNAME {}".format(name))

    def __str__(self):
        return "{} ({})".format(self.name, self.inst_sn)


if __name__ == "__main__":
    ls = Module(port="/dev/ttyUSB0")
    print (ls)
    
 
