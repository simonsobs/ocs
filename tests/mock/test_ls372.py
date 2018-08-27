"""Tests for Lakeshore 372 drive module."""

from ocs.Lakeshore.Lakeshore372 import LS372 as LS372_Base


class LS372(LS372_Base):
    """Fake LS372 for testing software."""
    def __init__(self, ip):
        """Initialize some attributes in any way, tests should manipulate these
        for their particular test case."""
        self.ip = ip
        self.id = "MOCK"
        self.autoscan = True

    def msg(self, message):
        """Overload the msg module and provide mock responses like the Lakeshore would provide."""
        _input = message.split(' ')  # commands will be separated by space from input parameters
        cmd = _input[0]

        responses = {"SCAN?": "02,{}".format(int(self.autoscan)),
                     "SCAN": ''}
        return responses[cmd]


# These use set_autoscan, which we should get rid of, but changing now requires
# mocking channels as well, which I'll do later.
def test_scanner_off():
    ls = LS372('172.16.127.192')
    ls._set_autoscan(autoscan=0)
    assert ls.get_autoscan() is False

def test_scanner_on():
    ls = LS372('172.16.127.192')
    ls._set_autoscan(autoscan=1)
    assert ls.get_autoscan() is True
