"""Tests for Lakeshore 372 drive module.

Note: While these test try, they don't neccessarily maintain the state the
Lakeshore was in when you started the test. If you're testing on a Lakeshore
unit that is being used for something, you'll probably want to reset the
parameters you require.
"""

from ocs.Lakeshore.Lakeshore372 import LS372, Channel

ls = LS372('172.16.127.192')
ch = Channel(ls, 4)


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


def test_set_get_curve():
    # TODO: Upload a curve first
    # if curve doesn't exist, it gets set to 0, for now we know 21 exists
    ch.set_calibration_curve(21)
    assert ch.get_calibration_curve() == 21


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

    init_range = ch.range
    ch.set_resistance_range(init_range*3)
    assert ch.get_resistance_range() == get_closest_range(init_range*3)
    ch.set_resistance_range(init_range)


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
