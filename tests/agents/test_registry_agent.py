import sys
sys.path.insert(0, '../agents/registry/')
from registry import Registry

import time
import pytest
import pytest_twisted
from unittest import mock

from ocs.ocs_agent import OpSession

import txaio
txaio.use_twisted()


@pytest.fixture
def agent():
    """Test fixture to setup a mocked OCSAgent."""
    mock_agent = mock.MagicMock()
    log = txaio.make_logger()
    txaio.start_logging(level='debug')
    mock_agent.log = log
    log.info('Initialized mock OCSAgent')
    agent = Registry(mock_agent)

    return agent


def create_session(op_name):
    """Create an OpSession with a mocked app for testing."""
    mock_app = mock.MagicMock()
    session = OpSession(1, op_name, app=mock_app)

    return session


@pytest_twisted.inlineCallbacks
def test_registry_main(agent):
    session = create_session('main')

    # Fake a heartbeat by directly registering an Agent
    # op_codes, feed
    heartbeat_example = [{"operation1": 5,
                          "operation2": 1},
                         {"agent_address": "observatory.test_agent",
                          "agg_params": {},
                          "feed_name": "heartbeat",
                          "address": "observatory.test_agent.feeds.heartbeat",
                          "record": False,
                          "session_id": str(time.time())}]
    agent._register_heartbeat(heartbeat_example)

    params = {'run_once': True}
    res = yield agent.main(session, params)

    assert res[0] is True


@pytest_twisted.inlineCallbacks
def test_registry_main_expire_agent(agent):
    session = create_session('main')

    # Fake a heartbeat by directly registering an Agent
    # op_codes, feed
    heartbeat_example = [{"operation1": 5,
                          "operation2": 1},
                         {"agent_address": "observatory.test_agent",
                          "agg_params": {},
                          "feed_name": "heartbeat",
                          "address": "observatory.test_agent.feeds.heartbeat",
                          "record": False,
                          "session_id": str(time.time())}]
    agent._register_heartbeat(heartbeat_example)

    # Make the last_updated time far enough in the past to expire
    agent.registered_agents['observatory.test_agent'].last_updated = \
        time.time() - 6.0

    params = {'run_once': True}
    res = yield agent.main(session, params)

    assert agent.registered_agents['observatory.test_agent'].expired is True
    assert res[0] is True


def test_registry_stop_main(agent):
    session = create_session('main')

    # Fake run main process
    agent._run = True

    res = agent._stop_main(session, params=None)
    assert res[0] is True


def test_registry_stop_main_not_running(agent):
    session = create_session('main')
    res = agent._stop_main(session, params=None)
    assert res[0] is False


def test_registry_register_agent(agent):
    session = create_session('main')
    agent_data = {'agent_address': 'observatory.test_agent'}
    res = agent._register_agent(session, agent_data)
    assert res[0] is True
