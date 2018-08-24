# Lakeshore372.py
# 6/6/2018
# Lauren Saunders
# Follows similar commands to Lakeshore240.py

import socket
import time


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
            c = Channel(self, i+1)
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
        :rtype: Channel Object
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


class Channel:
    """Lakeshore 372 Channel Object

    :param ls: Lakeshore unit for communication
    :type ls: LS372 Object
    :param channel_num: The channel number (1-8 or 1-16 depending on scanner
                        type)
    :type channel_num: int
    """
    def __init__(self, ls, channel_num):
        self.ls = ls
        self.channel_num = channel_num
        self.enabled = False
        self.get_input_channel_parameter()
        self.get_sensor_input_name()
        self.get_input_setup()

    def get_input_channel_parameter(self):
        """Run Input Channel Parameter Query

        ::

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

        self.enabled = bool(int(resp[0]))
        self.dwell = int(resp[1])  # seconds
        self.pause = int(resp[2])  # seconds
        self.curve_num = int(resp[3])
        self.tempco = tempco_key[resp[4]]

        return resp

    def get_input_setup(self):
        """Run Input Setup Query, storing results in human readable format.

        ::

          Input setup parameters include:
              mode - Sensor excitation mode.
                     Measurement input: 0 = Voltage Excitation Mode,
                                        1 = Current Excitation Mode
                     Control input (channel A): 1 = Current Excitation
                  type mode - int
              excitation - Measurement input excitation range
                  type excitation - int
              autorange - Specifies if auto range is enabled.
                              0 = off,
                              1 = autorange current,
                              2 = ROX102B Autorange (control input only)
                  type autorange - int
              range - Measurement input resistance. Ignored for control input.
                  type range - int
              cs shunt - Current source shunt.
                          0 = current source not shunted, excitation on
                          1 = current source shunted, excitation off
                  type cs shunt - int
              units - Specifies the preferred units parameter for sensor readings
                      and for the control setpoint:
                          1 = kelvin,
                          2 = ohms
                  type units - int

        :returns: response from INTYPE? command

        Reference: LakeShore 372 Manual - pg178-179
        """
        resp = self.ls.msg(f"INTYPE? {self.channel_num}").split(',')

        _mode = resp[0]
        _excitation = resp[1]
        _autorange = resp[2]
        _range = resp[3]
        _csshunt = resp[4]
        _units = resp[5]

        if self.channel_num == "A":
            control_channel = True
        else:
            control_channel = False

        mode_key = {'0': 'voltage',
                    '1': 'current'}

        self.mode = mode_key[_mode]

        if control_channel:
            # TODO: should test this with control channel connected
            excitation_key = {'1': {1: 316.0e-12,
                                    2: 1e-9,
                                    3: 3.16e-9,
                                    4: 10e-9,
                                    5: 31.6e-9,
                                    6: 100e-9}}
        else:
            excitation_key = {'0': {1: 2.0e-6,
                                    2: 6.32e-6,
                                    3: 20.0e-6,
                                    4: 63.2e-6,
                                    5: 200.0e-6,
                                    6: 632.0e-6,
                                    7: 2.0e-3,
                                    8: 6.32e-3,
                                    9: 20.0e-3,
                                    10: 63.2e-3,
                                    11: 200.0e-3,
                                    12: 632.0e-3},
                              '1': {1: 1.0e-12,
                                    2: 3.16e-12,
                                    3: 10.0e-12,
                                    4: 31.6e-12,
                                    5: 100.0e-12,
                                    6: 316.0e-12,
                                    7: 1.0e-9,
                                    8: 3.16e-9,
                                    9: 10.0e-9,
                                    10: 31.6e-9,
                                    11: 100.0e-9,
                                    12: 316.0e-9,
                                    13: 1.0e-6,
                                    14: 3.16e-6,
                                    15: 10.0e-6,
                                    16: 31.6e-6,
                                    17: 100.0e-6,
                                    18: 316.0e-6,
                                    19: 1.0e-3,
                                    20: 3.16e-3,
                                    21: 10.0-3,
                                    22: 31.6-3}}

        excitation_units_key = {'0': 'volts',
                                '1': 'amps'}

        self.excitation = excitation_key[_mode][int(_excitation)]
        self.excitation_units = excitation_units_key[_mode]

        autorange_key = {'0': 'on',
                         '1': 'off',
                         '2': 'ROX 102B'}
        self.autorange = autorange_key[_autorange]

        range_key = {1: 2.0e-3,
                     2: 6.32e-3,
                     3: 20.0e-3,
                     4: 63.2e-3,
                     5: 200e-3,
                     6: 632e-3,
                     7: 2.0,
                     8: 6.32,
                     9: 20.0,
                     10: 63.2,
                     11: 200,
                     12: 632,
                     13: 2e3,
                     14: 6.32e3,
                     15: 20.0e3,
                     16: 63.2e3,
                     17: 200e3,
                     18: 632e3,
                     19: 2e6,
                     20: 6.32e6,
                     21: 20.0e6,
                     22: 63.2e6}

        self.range = range_key[int(_range)]

        csshunt_key = {'0': 'on',
                       '1': 'off'}
        self.csshunt = csshunt_key[_csshunt]

        units_key = {'1': 'kelvin',
                     '2': 'ohms'}
        self.units = units_key[_units]

        return resp

    # Public API

    # INTYPE
    def set_excitation_mode(self, excitation_mode):
        pass

    def set_excitation(self, excitation_value):
        pass

    def enable_autorange(self):
        pass

    def disable_autorange(self):
        pass

    def set_resistance_range(self, resistance_range):
        pass

    def enable_excitation(self):
        pass

    def disable_excitation(self):
        pass

    # RDGPWR?
    def get_excitation_power(self):
        pass

    def set_units(self, units):
        pass

    # INSET
    def enable_channel(self):
        pass

    def disable_channel(self):
        pass

    def set_dwell(self, dwell):
        pass

    def set_pause(self, dwell):
        pass

    # Can also use INCRV/INCRV?
    def set_calibration_curve(self, curve_number):
        pass

    def get_calibration_curve(self):
        pass

    def set_temperature_coefficient(self, coefficient):
        pass

    # INNAME
    def get_sensor_input_name(self):
        """Run Sensor Input Name Query

        :returns: response from INNAME? command
        :rtype: str
        """
        resp = self.ls.msg(f"INNAME? {self.channel_num}").strip()

        self.name = resp

        return resp

    def set_sensor_input_name(self, name):
        pass

    # RDGK?
    def get_kelvin_reading(self):
        pass

    # RDGR?
    def get_resistance_reading(self):
        pass

    # RDGST?
    def get_reading_status(self):
        pass

    # SRDG?
    def get_sensor_reading(self):
        pass

    # TLIMIT
    def set_temperature_limit(self, limit):
        pass

    # TLIMIT?
    def get_temperature_limit(self):
        pass

    def __str__(self):
        string = "-" * 50 + "\n"
        string += "Channel %d: %s\n" % (self.channel_num, self.name)
        string += "-" * 50 + "\n"
        string += "\t%-30s\t%r\n" % ("Enabled :", self.enabled)
        string += "\t%-30s\t%s %s\n" % ("Dwell:", self.dwell, "seconds")
        string += "\t%-30s\t%s %s\n" % ("Pause:", self.pause, "seconds")
        string += "\t%-30s\t%s\n" % ("Curve Number:", self.curve_num)
        string += "\t%-30s\t%s\n" % ("Temperature Coefficient:", self.tempco)
        string += "\t%-30s\t%s\n" % ("Excitation State:", self.csshunt)
        string += "\t%-30s\t%s\n" % ("Excitation Mode:", self.mode)
        string += "\t%-30s\t%s %s\n" % ("Excitation:", self.excitation, self.excitation_units)
        string += "\t%-30s\t%s\n" % ("Autorange:", self.autorange)
        string += "\t%-30s\t%s %s\n" % ("Resistance Range:", self.range, "ohms")
        string += "\t%-30s\t%s\n" % ("Preferred Units:", self.units)

        return string


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
