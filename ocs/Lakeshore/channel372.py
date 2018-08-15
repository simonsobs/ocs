#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 15, 2018

@author: Brian Koopman
"""

class Channel372:
    """Lakeshore 372 Channel Object

    :param ls: Lakeshore unit for communication
    :type ls: LS372 Object
    :param channel_num: The channel number (1-8 or 1-16 depending on scanner type)
    :type channel_num: int
    """
    def __init__(self, ls, channel_num):
        self.ls = ls 
        self.channel_num = channel_num
        self.enabled = False
        self.query_input_channel_parameter()
        self.query_sensor_input_name()

    def query_input_channel_parameter(self):
        """Run Input Channel Parameter Query

        Input channel parameters include:
            off/on - Specifies whether the input/channel is disabled or enabled
                type off/on - bool
            dwell - Specifies a value for the autoscanning dwell time 1 to 200 s
                type dwell - int in units of seconds
            pause - Specifies a value for the change pause time: 3 to 200 s
                type pause - int in units of seconds
            curve number - Specifies which curve the channel uses
                type curve number - int
            tempco - Sets the temperature coefficien that will be used for
                     temperature control if no curve is selected
                type tempco - str

        :returns: response from INSET? command


        Reference: LakeShore 372 Manual - pg177
        """
        resp = self.ls.msg(f"INSET? {self.channel_num}").split(',')

        tempco_key = {'1': 'negative',
                      '2': 'positive'}

        self.enabled = bool(int(resp[0])) # bool
        self.dwell = int(resp[1]) # s
        self.pause = int(resp[2]) # s
        self.curve_num = int(resp[3])
        self.tempco = tempco_key[resp[4]]
        
        return resp

    def query_sensor_input_name(self):
        """Run Sensor Input Name Query

        :returns: response from INNAME? command
        :rtype: str
        """
        resp = self.ls.msg(f"INNAME? {self.channel_num}").strip()

        self.name = resp

        return resp

    def __str__(self):
        string  = "-" * 50 + "\n"
        string += "Channel %d: %s\n"%(self.channel_num, self.name)
        string += "-" * 50 + "\n"        
        string += "\t%-30s\t%r\n"%("Enabled :", self.enabled)
        string += "\t%-30s\t%s\n"%("Dwell:", self.dwell)
        string += "\t%-30s\t%s\n"%("Pause:", self.pause)
        string += "\t%-30s\t%s\n"%("Curve Number:", self.curve_num)
        string += "\t%-30s\t%s\n"%("Temperature Coefficient:", self.tempco)
        return string
    
if __name__ == "__main__":
    ch1 = Channel(None, 1)
    print(ch1)
    
