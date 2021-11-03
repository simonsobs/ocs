import sys
sys.path.insert(0, '../agents/influxdb_publisher/')
from influxdb_publisher import InfluxDBAgent

from unittest import mock

from util import create_session, create_agent_fixture, generate_data_for_queue


# fixtures
args = mock.MagicMock()
args.initial_state = 'idle'  # start idle so we can use a tmpdir for data_dir
args.host = 'localhost'
args.port = 8086
args.database = 'ocs_feeds'
args.protocol = 'line'
args.gzip = False

agent = create_agent_fixture(InfluxDBAgent, {'args': args})


class TestRecord:
    @mock.patch('ocs.agent.influxdb_publisher.InfluxDBClient',
                mock.MagicMock())
    def test_influxdb_publisher_record(self, agent):
        session = create_session('record')

        params = {'test_mode': True}
        res = agent.record(session, params)

        assert res[0] is True

    @mock.patch('ocs.agent.influxdb_publisher.InfluxDBClient',
                mock.MagicMock())
    def test_influxdb_publisher_record_data(self, agent, tmpdir):
        # repoint data_dir to tmpdir fixture
        agent.data_dir = tmpdir
        agent.aggregate = True

        session = create_session('record')

        # inject some data to the queue
        data = generate_data_for_queue()
        agent._enqueue_incoming_data(data)

        params = {'test_mode': True}
        res = agent.record(session, params)

        assert res[0] is True


def test_influxdb_publisher_enqueue_data_no_aggregate(agent, tmpdir):
    agent.aggregate = False

    data = generate_data_for_queue()
    agent._enqueue_incoming_data(data)

    assert agent.incoming_data.empty()


class TestStopRecord:
    def test_influxdb_publisher_stop_record_while_running(self, agent):
        session = create_session('record')
        agent.aggregate = True
        res = agent._stop_record(session, params=None)
        assert res[0] is True

    def test_influxdb_publisher_stop_record_not_running(self, agent):
        session = create_session('record')
        res = agent._stop_record(session, params=None)
        assert res[0] is False
