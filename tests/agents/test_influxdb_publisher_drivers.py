from ocs.common.influxdb_drivers import _format_field_line

import pytest


@pytest.mark.parametrize("key,value,result", [('fieldname', False, 'fieldname=False'),
                                              ('fieldname', 1, 'fieldname=1i'),
                                              ('fieldname', 4.2, 'fieldname=4.2'),
                                              ('fieldname', 'string', 'fieldname="string"')])
def test_publisher_format_field_line(key, value, result):
    f_line = _format_field_line(key, value)

    assert f_line == result
