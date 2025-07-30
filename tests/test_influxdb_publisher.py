import pytest

from ocs.agents.influxdb_publisher.drivers import Publisher
from ocs.common.influxdb_drivers import timestamp2influxtime


@pytest.mark.parametrize("t,protocol,expected",
                         [(1615389657.2904894, 'json', '2021-03-10T15:20:57.290489'),
                          (1615389657.2904894, 'line', 1615389657290489344)])
def test_timestamp2influxtime(t, protocol, expected):
    """Test converting timestamps to InfluxDB compatible formats."""
    assert timestamp2influxtime(t, protocol) == expected


def test_format_data():
    """Test passing int, float, string to InfluxDB line protocol."""

    # Not a real feed, but this is all we need for Publisher.format_data
    feed = {'agent_address': 'test_address',
            'feed_name': 'test_feed'}
    data = {'test': {'block_name': 'test',
                     'timestamps': [1615394417.3590388],
                     'data': {'key1': [1],
                              'key2': [2.3],
                              'key3': ["test"]},
                     }
            }

    expected = 'test_address,feed=test_feed key1=1i,key2=2.3,key3="test" 1615394417359038720'
    assert Publisher.format_data(data, feed, 'line')[0] == expected
