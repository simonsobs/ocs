import os

import pytest

from ocs.agents.influxdb_publisher.drivers import Publisher, timestamp2influxtime, _get_credentials


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


def test__get_credentials(tmp_path):
    # Defaults
    assert _get_credentials() == ('root', 'root')

    # Set from file
    d = tmp_path
    username_file = d / "username"
    username_file.write_text("admin", encoding="utf-8")
    password_file = d / "password"
    password_file.write_text("testpass", encoding="utf-8")

    os.environ['INFLUXDB_USERNAME_FILE'] = str(username_file)
    os.environ['INFLUXDB_PASSWORD_FILE'] = str(password_file)
    assert _get_credentials() == ('admin', 'testpass')

    # Set from env var
    os.environ['INFLUXDB_USERNAME'] = 'user_var'
    os.environ['INFLUXDB_PASSWORD'] = 'pass_var'
    assert _get_credentials() == ('user_var', 'pass_var')

    # Cleanup
    vars_ = ['INFLUXDB_USERNAME_FILE',
             'INFLUXDB_PASSWORD_FILE',
             'INFLUXDB_USERNAME',
             'INFLUXDB_PASSWORD']
    for v in vars_:
        os.environ.pop(v)
