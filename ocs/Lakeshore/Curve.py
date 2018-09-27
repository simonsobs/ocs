#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 21:05:48 2018

@author: jacoblashner
"""

import numpy as np
from collections import OrderedDict

class Curve:
    """
    Header for calibration curve
    ----------------
    :Sensor Model:      Name of curve
    :Serial Number:        Serial Number
    :Data Format:    2 = V:K, 3 = Ohms:K, 4 = log(Ohms):K
    :SetPoint Limit:     Temperature Limit (in K)
    :Temperature Coefficient:     1 = negative, 2 = positive
    :Number of Breakpoints:     Number of curve points
    """
    def __init__(self, filename=None, header=None, breakpoints=None):

        if filename is not None:
            self.load_from_file(filename)
        else:
            if header and breakpoints:
                self.header = header
                self.breakpoints = breakpoints
            else:
                raise Exception("Must give either filename or header and breakpoints")

    def load_from_file(self, filename):
        with open(filename, 'r') as file:
            content = file.readlines()

        header = OrderedDict({})
        for line in content:
            if line.strip()=='':
                break
            key, v = line.split(':')
            val = v.split('(')[0]
            header[key] = val

        self.breakpoints = []
        for line in content[9:]:
            num, unit, temp = line.split()
            self.breakpoints.append((float(unit), float(temp)))

    def __str__(self):
        string = ""
        for key, val in self.header.items():
            string += "%-15s: %s\n"%(key, val)
        return string

if __name__ == "__main__":
    filename = "D-001.cal"
    curve = Curve(filename=filename)
    
    
            
            
    
    
