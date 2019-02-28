"""Tests for Lakeshore 372 drive module.

Note: Do not run on a Lakeshore controlling heaters in a cryostat, as it will
likely have ill effects! You have been warned.

Note: While these test try, they don't neccessarily maintain the state the
Lakeshore was in when you started the test. If you're testing on a Lakeshore
unit that is being used for something, you'll probably want to reset the
parameters you require.
"""

import time
from ocs.Lakeshore.Lakeshore372 import LS372, Channel, Curve, Heater

ls = LS372('10.10.10.3')
ch = Channel(ls, 4)
cv = Curve(ls, 21)
ht = Heater(ls, 0)

# Heater Tests
def test_set_get_heater_input():
    init_value = ht.get_input_channel()
    ht.set_input_channel('1')
    assert ht.input == '1'
    ht.set_input_channel(2)
    assert ht.input == '2'
    ht.set_input_channel(init_value)


def test_set_get_heater_range():
    init_value = ht.get_heater_range()
    ht.set_heater_range(31.6e-6)
    assert ht.range == 31.6e-6
    ht.set_heater_range(100e-6)
    assert ht.range == 100e-6
    ht.set_heater_range(init_value)


def test_set_get_heater_mode():
    init_value = ht.get_mode()
    ht.set_mode("Open Loop")
    assert ht.mode.lower() == 'open loop'
    ht.set_mode("Closed Loop")
    assert ht.mode.lower() == 'closed loop'
    ht.set_mode(init_value)


# Curve Tests
def test_set_get_curve(tmpdir):
    tmp_file = tmpdir.mkdir("curve").join('curve.txt')
    cv.get_curve(tmp_file)
    cv.set_curve("./test_ls372/test.cal")
    assert cv.name == "UNIT TEST"
    assert cv.serial_number == "00000042"
    cv.set_curve(tmp_file)


def test_set_get_curve_coefficient():
    init_coefficient = cv.get_coefficient()
    cv.set_coefficient('positive')
    assert cv.get_coefficient() == 'positive'
    cv.set_coefficient(init_coefficient)


def test_set_get_curve_limit():
    init_limit = cv.get_limit()
    cv.set_limit(42.0)
    assert cv.get_limit() == 42.0
    cv.set_limit(init_limit)


def test_set_get_curve_format():
    init_format = cv.get_format()
    cv.set_format("Ohm/K (cubic spline)")
    assert cv.get_format() == "Ohm/K (cubic spline)"
    cv.set_format(init_format)


def test_set_get_curve_serial_number():
    init_sn = cv.get_serial_number()
    cv.set_serial_number("10001110101")
    assert cv.get_serial_number() == "0001110101"
    cv.set_serial_number(init_sn)


def test_set_get_curve_name():
    init_name = cv.get_name()
    cv.set_name("unit test")
    assert cv.get_name().lower() == "unit test"
    cv.set_name(init_name)


# LS372 Tests
def test_scanner_off():
    init_autoscan = ls.get_autoscan()
    ls.disable_autoscan()
    assert ls.get_autoscan() is False
    if init_autoscan:
        ls.enable_autoscan()
    else:
        pass


def test_scanner_on():
    init_autoscan = ls.get_autoscan()
    ls.enable_autoscan()
    assert ls.get_autoscan() is True
    if init_autoscan:
        pass
    else:
        ls.disable_autoscan()


# Channel Tests
def test_enable_autorange():
    init_autorange = ch.autorange
    ch.enable_autorange()
    assert ch.autorange == 'on'
    if init_autorange == 'on':
        pass
    else:
        ch.disable_autorange()


def test_disable_autorange():
    init_autorange = ch.autorange
    ch.disable_autorange()
    assert ch.autorange == 'off'
    if init_autorange == 'off':
        pass
    else:
        ch.enable_autorange()


def test_set_get_excitation_mode():
    init_mode = ch.mode

    ch.set_excitation_mode('voltage')
    ch.get_excitation_mode()
    assert ch.mode == 'voltage'

    ch.set_excitation_mode('current')
    ch.get_excitation_mode()
    assert ch.mode == 'current'

    ch.set_excitation_mode(init_mode)


def test_enable_channel():
    init_state = ch.enabled

    ch.enable_channel()
    ch.get_input_channel_parameter()
    assert ch.enabled is True

    if init_state:
        pass
    else:
        ch.disable_channel()


def test_disable_channel():
    init_state = ch.enabled

    ch.disable_channel()
    ch.get_input_channel_parameter()
    assert ch.enabled is False

    if init_state:
        ch.enable_channel()
    else:
        pass


def test_set_get_dwell():
    init_dwell = ch.get_dwell()
    ch.set_dwell(10)
    assert ch.get_dwell() == 10
    ch.set_dwell(init_dwell)


def test_set_get_pause():
    init_pause = ch.get_pause()
    ch.set_pause(10)
    assert ch.get_pause() == 10
    ch.set_pause(init_pause)


def test_set_get_tempco_positive():
    # If curve sets coefficient, we can't, so unset curve.
    ch.set_calibration_curve(0)
    ch.set_temperature_coefficient('positive')
    assert ch.get_temperature_coefficient() == 'positive'


def test_set_get_tempco_negative():
    # If curve sets coefficient, we can't, so unset curve.
    ch.set_calibration_curve(0)
    ch.set_temperature_coefficient('negative')
    assert ch.get_temperature_coefficient() == 'negative'


def test_set_get_input_name():
    init_name = ch.get_sensor_input_name()
    ch.set_sensor_input_name("Test 04")
    assert ch.get_sensor_input_name() == "Test 04"
    ch.set_sensor_input_name(init_name)


def test_set_get_temperature_limit():
    starting_tlimit = ch.get_temperature_limit()
    ch.set_temperature_limit(20)
    assert ch.get_temperature_limit() == 20.0
    ch.set_temperature_limit(starting_tlimit)


def test_set_get_units():
    init_units = ch.get_units()
    ch.set_units('kelvin')
    assert ch.get_units() == 'kelvin'
    ch.set_units(init_units)


def test_enable_excitation():
    init_excitation = ch.csshunt
    ch.enable_excitation()
    ch.get_input_setup()
    assert ch.csshunt == 'on'
    if init_excitation == 'on':
        pass
    else:
        ch.disable_excitation()


def test_disable_excitation():
    init_excitation = ch.csshunt
    ch.disable_excitation()
    ch.get_input_setup()
    assert ch.csshunt == 'off'
    if init_excitation == 'off':
        pass
    else:
        ch.enable_excitation()

def test_set_get_resistance_range():
    """Test setting the resistance range. This can't exactly be an arbitrary
    setting. If it's too low (if the excitation isn't high enough) then it just
    won't change and probably you won't catch the error either.

    This avoids the issue by setting the range to the next highest setting,
    which I think should almost always work.
    """
    def get_closest_range(num):
        """Gets the closest valid resistance range."""
        ranges = [2.0e-3, 6.32e-3, 20.0e-3, 63.2e-3, 200e-3, 632e-3, 2.0,
                  6.32, 20.0, 63.2, 200, 632, 2e3, 6.32e3, 20.0e3, 63.2e3,
                  200e3, 632e3, 2e6, 6.32e6, 20.0e6, 63.2e6]

        return min(ranges, key=lambda x: abs(x-num))

    # turn off autoscan (but remember if we had to)
    init_autoscan = ls.get_autoscan()
    ls.disable_autoscan()

    # check autorange setting
    init_autorange = ch.autorange

    # enable auto_range (which should make increasing by one safe)
    ch.enable_autorange()
    time.sleep(3) # wait for autorange to settle
    ch.disable_autorange()

    init_range = ch.range
    ch.set_resistance_range(init_range*3)
    assert ch.get_resistance_range() == get_closest_range(init_range*3)
    ch.set_resistance_range(init_range)

    # turn back on autorange if it was on
    if init_autorange == 'on':
        ch.enable_autorange()

    # turn back on autoscan if it was on
    if init_autoscan:
        ls.enable_autoscan()

def test_set_get_excitation():
    """Test setting the excitation. We try to set it to the lowest setting to
    be safe."""
    init_excitation = ch.get_excitation()
    _mode = ch.mode
    ch.set_excitation(2e-20)
    if _mode == 'voltage':
        assert ch.get_excitation() == 2e-6
    elif _mode == 'current':
        assert ch.get_excitation() == 1e-12
    else:
        assert True is False, "Unknown excitation mode -- this shouldn't happen"

    ch.set_excitation(init_excitation)
