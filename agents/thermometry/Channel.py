#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 13:42:09 2018

@author: jacoblashner
"""


from Curve import Curve

# ==============================================================================
# Lots of stuff to convert between integers that are read by the module 
# and what the integers actually stand for
# ==============================================================================

# To convert from int representation to string and back
sensors = {"Diode":1, "PlatRTC":2, "NTCRTC": 3}
# units = {"Kelvin": 1, "Celsius": 2, "Sensor": 3, "Fahrenheit": 4}
sensorStrings = ["Diode", "PlatRTC", "NTCRTC"]
unitStrings = ["Kelvin", "Celsius", "Sensor", "Fahrenheit"]

# To convert from int representation to excitation or range
# use:   ranges[sensorType][range]
excitations = [[10e-6], [1e-3], [1e-3, 300e-6, 100e-6, 30e-6, 10e-6, 3e-6, 1e-6, 300e-9, 100e-9]]
ranges = [[7.5], [1e3], [10, 30, 100, 300, 1e3, 3e3, 10e3, 30e3, 100e3]] 

    
class Channel:
    """
        Object for each channel of the lakeshore module
        
        Properties
        --------------
        :channel_num: The number of the channel (1-8). This should not be changed once set
        :name: Specifies name of channel
        :sensor (int): 1 = Diode, 2 = PlatRTC, 3 = NTC RTD
        :auto_range: Specifies if channel should use autorange (1,0).
        :range: Specifies range if auto_range is false (0-8). Range is accoriding to Lakeshore docs.
        :current_reversal: Specifies if current reversal should be used (0, 1). Should be 0 for diode.
        :unit: 1 = K, 2 = C, 3 = Sensor, 4 = F
        :enabled: Sets whether channel is enabled. (1,0)
                
    """
    def __init__(self, ls, channel_num, enabled = False):
        self.ls = ls 
        self.channel_num = channel_num
        self.enabled = enabled
        self.read_info()

    def update_info(self):
        self.ls.msg(f"INNAME {self.name}")

        input_type_message = "INTYPE "
        input_type_message += ",".join([self.channel_num, self.sensor, self.auto_range,
                                        self.range, self.current_reversal, self.unit, self.enabled])

        self.ls.msg(input_type_message)
        
    def get_reading(self, unit=0):
        u = self.unit if not unit else unit
        unit_char = "KCSF"[u-1]
        message = f"{unit_char}RDG? {self.channel_num}"
        response = self.ls.msg(message)
        return float(response)
    
    def read_info(self):
        response = self.ls.msg(f"INTYPE? {self.channel_num}")

#        response = "1,0,0,0,1"
        data = response.split(',')

        self.sensor = int(data[0])
        self.auto_range = int(data[1])
        self.range = int(data[2])
        self.current_reversal = int(data[3])
        self.unit  = int(data[4])
        
        response = self.ls.msg("INNAME? %d"%(self.channel_num))
        self.name = response
        
    def load_curve_point(self, n, x, y):
        """ Loads point n in the curve for specified channel"""
        message = "CRVPT "
        message += ",".join([str(c) for c in [self.channel_num, n, x, y]])
        self.ls.msg(message)
        
    def load_curve(self, filename):
        self.curve = Curve(filename=filename)

        units = self.curve.units
        temps = self.curve.temps

        assert len(units) == len(temps)
        assert len(units) < 200, "Curve must have less than 200 pts"

        print (f"Loading Curve to {self.name}")
        for i in range(200):
            if i < len(units):
                self.load_curve_point(i+1, units[i], temps[i])
            else:
                self.load_curve_point(i+1, 0, 0)
    
    def __str__(self):
        string  = "-" * 40 + "\n"
        string += "Channel %d: %s\n"%(self.channel_num, self.name)
        string += "-"*40 + "\n"        
        string += "\t%-16s\t%s\n"%("Sensor:", sensorStrings[self.sensor - 1])

        string += "\t%-16s\t%r\n"%("Auto Range:", bool(self.auto_range))
        
        if not self.auto_range:
            string += "\t%-16s\t%.1e Amps\n"%("Excitation:", excitations[self.sensor - 1][self.range - 1])
            unit    = "Volt" if self.sensor == 1 else "Ohms"
            string += "\t%-16s\t%.1e %s\n"%("Range:", ranges[self.sensor - 1][self.range - 1], unit)
        
        string += "\t%-16s\t%r\n"%("Current Reversal:", bool(self.current_reversal))
        string += "\t%-16s\t%s\n"%("Unit:", unitStrings[self.unit - 1])
        return string
        
    
if __name__ == "__main__":
    ch1 = Channel(None, 1)
    print(ch1)
    