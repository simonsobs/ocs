#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 21:05:48 2018

@author: jacoblashner
"""

import numpy as np
import matplotlib.pyplot as plt
import numpy as np
class Curve:
    """
    Header for curve
    ----------------
    :Name:      Name of curve
    :SN:        Serial Number
    :Format:    2 = V:K, 3 = Ohms:K, 4 = log(Ohms):K
    :Limit:     Temperature Limit (in K)
    :Coeff:     1 = negative, 2 = positive
    
    """
    def __init__(self, fname, excitation):
        self.header = {}
        
        with open(fname, 'r') as f:
            # Reads Header
            lineNum = 0
            while True:
                lineNum += 1
                line = f.readline().strip()
                if line == "[DATA]":
                    break
                
                if ':' in line:
                    key = line.split(':')[0].strip()
                    val = line.split(':')[1].strip()
                    self.header[key] = val
                
            self.nums, unit, self.temps = np.loadtxt(fname, skiprows = lineNum,
                                                        unpack = True)
        
            if int(self.header["Format"]) == 2:
                self.ohms = unit / excitation 
            elif int(self.header["Format"]) == 3:
                self.ohms = unit
            elif int(self.header["Format"]) == 4:
                self.ohms = np.power(10, unit)
            

    
    def __str__(self):
        string = ""
        for k in self.header.keys():
            string += "%-15s: %s\n"%(k, self.header[k])
        return string
    
    
if __name__ == "__main__":
    fname = "curves/defaults/SimSensorNTC.txt"
    curve = Curve(None, fname = fname)
    curve.loadToMachine(None, 1)


    
    
            
            
    
    