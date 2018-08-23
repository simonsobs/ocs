# Lakeshore372.py
# 6/6/2018
# Lauren Saunders
# Follows similar commands to Lakeshore240.py

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
        # Enable all channels
        #  going to hold off on enabling all channels automatically - bjk
        # for i in range(self.num_channels):
        #     print(i)
        #     self.msg('INSET %d,1,3,3'%(i))

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

    def get_temp(self, unit="S", chan=-1):
        if (chan == -1):
            resp = self.msg("SCAN?")
            c = resp.split(',')[0]
        elif (chan == 0):
            c = 'A'
        else:
            c = str(chan)

        if unit == 'S':
            # Sensor is same as Resistance Query
            return float(self.msg('SRDG? %s' % c))
        if unit == 'K':
            return float(self.msg('KRDG? %s' % c))

    # SCAN?
    def get_autoscan(self):
        pass

    def set_autoscan(self, start=1, autoscan=0):
        self.msg('SCAN {},{}'.format(start, autoscan))

    def enable_autoscan(self):
        """Enable the autoscan feature of the Lakeshore 372.

        Will query active channel to pass already selected channel to SCAN
        command.
        """
        active_channel = self.get_active_channel()
        self.msg('SCAN {},{}'.format(active_channel.channel_num, 1))

    def disable_autoscan(self):
        """Disable the autoscan feature of the Lakeshore 372.

        Will query active channel to pass already selected channel to SCAN
        command.
        """
        active_channel = self.get_active_channel()
        self.msg('SCAN {},{}'.format(active_channel.channel_num, 0))

    def get_active_channel(self):
        """Query the Lakeshore for which channel it's currently scanning.

        :returns: channel object describing the scanned channel
        :rtype: Channel372 Object
        """
        resp = self.msg("SCAN?")
        channel_number = int(resp.split(',')[0])
        channel_list = [_.channel_num for _ in self.channels]
        idx = channel_list.index(channel_number)
        return self.channels[idx]

    def set_active_channel(self, channel):
        """Set the active scanner channel.

        Query using SCAN? to determine autoscan parameter and set active
        channel.

        :param channel: Channel number to switch scanner to. 1-8 or 1-16
                        depending on scanner type
        :type channel: int
        """
        resp = self.msg("SCAN?")
        autoscan_setting = resp.split(',')[1]
        self.msg('SCAN {},{}'.format(channel, autoscan_setting))

    # NET?
    def get_network_settings(self):
        pass

    # NETID?
    def get_network_configuration(self):
        pass

    # PID
    def set_pid(self, P, I, D):
        pass

    # PID?
    def get_pid(self):
        pass


class Curve:
    """Calibration Curve class for the LS372."""
    # CRVHDR?
    def get_header(self):
        pass

    # CRVHDR
    def set_header(self, name, serial_number, _format, limit, coefficient):
        pass

    # CRVPT?
    def get_data_point(self, index):
        pass

    # CRVPT
    # TODO: find out what curvature value does (it is optional)
    def set_data_point(self, index, units_value, kevlin_value, curvature_value=None):
        pass

    # Public API Elements
    def get_curve(self):
        pass

    def set_curve(self, _file):
        pass

    # CRVDEL
    def delete_curve(self):
        pass


class Heater:
    """Heater class for LS372 control"""
    def __init__(self, ls, output):
        self.ls = ls
        self.output = output
        self.mode = None
        self.input = None
        self.powerup = None
        self.filter = None
        self.delay = None

    # OUTMODE
    def set_output_mode(self, output, mode, _input, powerup, polarity, _filter, delay):
        pass

    # OUTMODE?
    def get_output_mode(self):
        pass

    # HTRSET/HTRSET?
    def get_heater_output(self, heater):
        pass

    # Presumably we're going to know and have set values for heat resistance,
    # max current, etc, maybe that'll simplify this in the future.
    def set_heater_output(self, heater, resistance, max_current, max_user_current, current):
        pass

    def get_heater_setup(self, heater):
        pass

    # RAMP, RAMP? - in heater class
    def set_ramp_rate(self, rate):
        pass

    def get_ramp_rate(self, rate):
        pass

    def enable_ramp(self):
        pass

    def disable_ramp(self):
        pass

    # RAMPST?
    def get_ramp_status(self):
        pass

    # RANGE, RANGE?
    def set_heater_range(self, _range):
        pass

    def get_heater_range(self):
        pass

    # SETP - heater class
    def set_setpoint(self, value):
        pass

    # SETP? - heater class
    def get_setpoint(self):
        pass

    # STILL - heater class?
    def set_still_output(self, value):
        pass

    # STILL? - heater_class?
    def get_still_output(self):
        pass

    # ANALOG, ANALOG?, AOUT?
    # TODO: read up on what analog output is used for, pretty sure just another output
    def get_analog_output(self):
        pass

    def set_analog_output(self):
        pass


if __name__ == "__main__":
    import json
    with open("ips.json") as file:
        ips = json.load(file)
    name="LS372A"
    ls = LS372(ips[name])
