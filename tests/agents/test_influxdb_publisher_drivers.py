from ocs.agents.influxdb_publisher.drivers import Publisher

import pytest


@pytest.mark.parametrize("key,value,result", [('fieldname', False, 'fieldname=False'),
                                              ('fieldname', 1, 'fieldname=1i'),
                                              ('fieldname', 4.2, 'fieldname=4.2'),
                                              ('fieldname', 'string', 'fieldname="string"')])
def test_publisher_format_field_line(key, value, result):
    f_line = Publisher._format_field_line(key, value)

    assert f_line == result
