import sys
sys.path.insert(0, '../agents/influxdb_publisher/')
from influxdb_publisher import InfluxDBAgent

import time
from unittest import mock

from util import create_session, create_agent_fixture


# fixtures
args = mock.MagicMock()
args.initial_state = 'idle'  # start idle so we can use a tmpdir for data_dir
args.host = 'localhost'
args.port = 8086
args.database = 'ocs_feeds'
args.protocol = 'line'
args.gzip = False

agent = create_agent_fixture(InfluxDBAgent, {'args': args})


@mock.patch('ocs.agent.influxdb_publisher.InfluxDBClient', mock.MagicMock())
def test_influxdb_publisher_record(agent):
    session = create_session('record')

    params = {'run_once': True}
    res = agent.record(session, params)

    assert res[0] is True


@mock.patch('ocs.agent.influxdb_publisher.InfluxDBClient', mock.MagicMock())
def test_influxdb_publisher_record_data(agent, tmpdir):
    # repoint data_dir to tmpdir fixture
    agent.data_dir = tmpdir
    agent.aggregate = True

    session = create_session('record')

    # inject some data to the queue
    data = {'temps': {'block_name': 'test',
                      'data': {'field_0': [1, 2],
                               'field_01': [3, 4]},
                      'timestamps': [time.time(), time.time()+1]}}
    feed = {'agent_address': 'observatory.test-agent1',
            'agg_params': {'frame_length': 60},
            'feed_name': 'test_feed',
            'address': 'observatory.test-agent1.feeds.test_feed',
            'record': True,
            'session_id': str(time.time())}
    _data = (data, feed)
    agent._enqueue_incoming_data(_data)

    params = {'run_once': True}
    res = agent.record(session, params)

    assert res[0] is True


def test_influxdb_publisher_enqueue_data_no_aggregate(agent, tmpdir):
    agent.aggregate = False

    data = {'temps': {'block_name': 'test',
                      'data': {'field_0': [1, 2],
                               'field_01': [3, 4]},
                      'timestamps': [time.time(), time.time()+1]}}
    feed = {'agent_address': 'observatory.test-agent1',
            'agg_params': {'frame_length': 60},
            'feed_name': 'test_feed',
            'address': 'observatory.test-agent1.feeds.test_feed',
            'record': True,
            'session_id': str(time.time())}
    _data = (data, feed)
    agent._enqueue_incoming_data(_data)

    assert agent.incoming_data.empty()


def test_influxdb_publisher_stop_record(agent):
    session = create_session('record')
    agent.aggregate = True
    res = agent._stop_record(session, params=None)
    assert res[0] is True


def test_influxdb_publisher_stop_record_not_running(agent):
    session = create_session('record')
    res = agent._stop_record(session, params=None)
    assert res[0] is False
