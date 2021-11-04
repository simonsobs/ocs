import sys
sys.path.insert(0, '../agents/aggregator/')

import pytest
from unittest import mock

from util import create_session, create_agent_fixture, generate_data_for_queue

try:
    # depends on spt3g
    from aggregator_agent import AggregatorAgent

    args = mock.MagicMock()
    args.time_per_file = 3
    args.data_dir = '/tmp/data'
    # start idle so we can use a tmpdir for data_dir
    args.initial_state = 'idle'

    agent = create_agent_fixture(AggregatorAgent, {'args': args})
except ModuleNotFoundError as e:
    print(f"Unable to import: {e}")


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
class TestRecord:
    def test_aggregator_agent_record_no_data(self, agent, tmpdir):
        # repoint data_dir to tmpdir fixture
        agent.data_dir = tmpdir

        session = create_session('record')

        params = {'test_mode': True}
        res = agent.record(session, params)

        assert res[0] is True

    def test_aggregator_agent_record_data(self, agent, tmpdir):
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

        assert 'current_file' in session.data
        assert 'providers' in session.data
        assert 'observatory.test-agent1.feeds.test_feed' in session.data['providers']
        assert session.data['providers']['observatory.test-agent1.feeds.test_feed']['stale'] is False
        assert session.data['providers']['observatory.test-agent1.feeds.test_feed']['last_block_received'] == 'temps'


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
def test_aggregator_agent_enqueue_data_no_aggregate(agent):
    agent.aggregate = False

    data = generate_data_for_queue()
    agent._enqueue_incoming_data(data)

    assert agent.incoming_data.empty()


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
class TestStopRecord:
    def test_aggregator_agent_stop_record_while_running(self, agent):
        session = create_session('record')
        agent.aggregate = True
        res = agent._stop_record(session, params=None)
        assert res[0] is True

    def test_aggregator_agent_stop_record_not_running(self, agent):
        session = create_session('record')
        res = agent._stop_record(session, params=None)
        assert res[0] is False
