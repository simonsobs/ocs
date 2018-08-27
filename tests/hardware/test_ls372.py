"""Tests for Lakeshore 372 drive module.

Note: This doesn't neccessarily maintain the state the Lakeshore was in when
you started the test. If you're testing on a Lakeshore unit that is being used
for something, you'll likely have to reset the parameters you require.
"""

from ocs.Lakeshore.Lakeshore372 import LS372, Channel

ls = LS372('172.16.127.192')
ch = Channel(ls, 4)

def test_scanner_off():
    ls.disable_autoscan()
    assert ls.get_autoscan() is False

def test_scanner_on():
    ls.enable_autoscan()
    assert ls.get_autoscan() is True

def test_enable_autorange():
    ch.enable_autorange()
    assert ch.autorange == 'on'

def test_disable_autorange():
    ch.disable_autorange()
    assert ch.autorange == 'off'

def test_set_get_excitation_mode_voltage():
    ch.set_excitation_mode('voltage')
    ch.get_excitation_mode()
    assert ch.mode == 'voltage'

def test_set_get_excitation_mode_current():
    ch.set_excitation_mode('current')
    ch.get_excitation_mode()
    assert ch.mode == 'current'

def test_enable_channel():
    ch.enable_channel()
    ch.get_input_channel_parameter()
    assert ch.enabled is True

def test_disable_channel():
    ch.disable_channel()
    ch.get_input_channel_parameter()
    assert ch.enabled is False

