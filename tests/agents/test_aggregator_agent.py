import sys
sys.path.insert(0, '../agents/aggregator/')
from aggregator_agent import AggregatorAgent

from unittest import mock

from util import create_session, create_agent_fixture, generate_data_for_queue

# fixtures
args = mock.MagicMock()
args.time_per_file = 3
args.data_dir = '/tmp/data'
args.initial_state = 'idle'  # start idle so we can use a tmpdir for data_dir

agent = create_agent_fixture(AggregatorAgent, {'args': args})


def test_aggregator_agent_record(agent, tmpdir):
    # repoint data_dir to tmpdir fixture
    agent.data_dir = tmpdir

    session = create_session('record')

    params = {'run_once': True}
    res = agent.record(session, params)

    assert res[0] is True


def test_aggregator_agent_record_data(agent, tmpdir):
    # repoint data_dir to tmpdir fixture
    agent.data_dir = tmpdir
    agent.aggregate = True

    session = create_session('record')

    # inject some data to the queue
    data = generate_data_for_queue()
    agent._enqueue_incoming_data(data)

    params = {'run_once': True}
    res = agent.record(session, params)

    assert res[0] is True


def test_aggregator_agent_enqueue_data_no_aggregate(agent):
    agent.aggregate = False

    data = generate_data_for_queue()
    agent._enqueue_incoming_data(data)

    assert agent.incoming_data.empty()


def test_aggregator_agent_stop_record(agent):
    session = create_session('record')
    agent.aggregate = True
    res = agent._stop_record(session, params=None)
    assert res[0] is True


def test_aggregator_agent_stop_record_not_running(agent):
    session = create_session('record')
    res = agent._stop_record(session, params=None)
    assert res[0] is False
