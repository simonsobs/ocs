import sys
sys.path.insert(0, '../agents/fake_data/')
from fake_data_agent import FakeDataAgent

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
    agent = FakeDataAgent(mock_agent)

    return agent


def create_session(op_name):
    """Create an OpSession with a mocked app for testing."""
    mock_app = mock.MagicMock()
    session = OpSession(1, op_name, app=mock_app)

    return session


def test_fake_data_set_heartbeat(agent):
    session = create_session('set_heartbeat')
    res = agent.set_heartbeat(session, {'heartbeat': True})
    print(res)
    print(session.encoded())
    assert res[0] is True


def test_fake_data_acq(agent):
    session = create_session('acq')
    params = {'run_once': True}
    res = agent.acq(session, params=params)
    assert res[0] is True


def test_fake_data_stop_acq(agent):
    session = create_session('acq')
    res = agent._stop_acq(session, params=None)
    assert res[0] is False


def test_fake_data_stop_acq_while_running(agent):
    session = create_session('acq')

    # set running job to 'acq'
    agent.job = 'acq'

    res = agent._stop_acq(session, params=None)
    assert res[0] is True


@pytest_twisted.inlineCallbacks
def test_fake_data_delay_task(agent):
    session = create_session('delay_task')
    params = {'delay': 0.001, 'succeed': True}
    res = yield agent.delay_task(session, params=params)
    assert res[0] is True


def test_fake_data_try_set_job_running_job(agent):
    session = create_session('acq')

    # set running job to 'acq'
    agent.job = 'acq'

    res = agent.try_set_job('not_acq')

    assert res[0] is False
