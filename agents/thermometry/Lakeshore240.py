#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 14:15:51 2018

@author: jacoblashner
"""

import serial
import time
import numpy as np
from Channel import Channel

try:
    from tqdm import *
except:
    tqdm = lambda x : x
       

class Module:
    """
        Allows communication to Lakeshore Module.
        Contains list of inputs which can be read from.
    """
    
    def __init__(self, port = '/dev/tty.SLAB_USBtoUART', 
                 baud = 115200, timeout = 1, numChannels = 2):
        """
            Establish Serial communication and initialize channels.
        """
        self.com = serial.Serial(port = port, baudrate = baud, timeout = timeout)
        self.idn = self.test()
        self.channels = []
        for i in range(numChannels):
            c = Channel(self, i+1, enabled = True)
            c.name = "Input %d"%(i+1)
            c.updateInfo()
            self.channels.append(c)
            
    def msg(self, msg):
        """
            Send command or query to module. 
            Return response (within timeout) if message is a query.
        """
        
        tmp = msg + '\r\n;'
        bits = tmp.encode()
        
        # open if need to (should need to as it's a bad idea to leave open permanently)
        if not self.com.isOpen():
            self.com.open()
        self._flush()

        # send command to lakeshore
        self.com.write(bits)
        
        # Reads response if queried
        resp = ''
        if "?" in msg:
            resp = self.com.readline()
            resp = str(resp[:-2], 'utf-8');         #Strips terminating chars
            if not resp:
                resp = "ERROR: Response timeout"
        
        time.sleep(.01)                 #Must wait 10 ms before another command
        
        self.com.close()
    
        return resp            
    
    def test(self):
        """ Return IDN of module. """
        return self.msg("*IDN?")
    
    def __str__(self):
        idn = self.test()
        string = "ID: %s"%idn
        string += "\n"
        for c in self.channels:
            string += str(c)
        
        return string
    
    def _flush(self):
        self.com.flushInput()
        self.com.flushOutput()
        
        
        
    def close(self):
        """ Closes device """
        try:
            if self.com.isOpen():
                self.com.close()
        except:
            raise LakeshoreError('Could not close down connection')

    

if __name__ == "__main__":
    ls = Module()
    print (ls.idn)

    
    
 