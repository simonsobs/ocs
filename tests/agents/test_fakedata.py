from ocs.agents.fake_data.agent import FakeDataAgent

import pytest_twisted

from agents.util import create_session, create_agent_fixture


# fixtures
agent = create_agent_fixture(FakeDataAgent)


def test_fake_data_set_heartbeat(agent):
    session = create_session('set_heartbeat')
    res = agent.set_heartbeat(session, {'heartbeat': True})
    print(res)
    print(session.encoded())
    assert res[0] is True


def test_fake_data_acq(agent):
    session = create_session('acq')
    params = {'test_mode': True}
    res = agent.acq(session, params=params)
    assert res[0] is True

    assert 'fields' in session.data
    assert 'timestamp' in session.data
    channels = ['channel_00', 'channel_01']
    assert all([ch in channels for ch in session.data['fields']])


class TestStopAcq:
    @pytest_twisted.inlineCallbacks
    def test_fake_data_stop_acq_not_running(self, agent):
        session = create_session('acq')
        res = yield agent._stop_acq(session, params=None)
        assert res[0] is False

    @pytest_twisted.inlineCallbacks
    def test_fake_data_stop_acq_while_running(self, agent):
        session = create_session('acq')

        # set running job to 'acq'
        agent.job = 'acq'

        res = yield agent._stop_acq(session, params=None)
        assert res[0] is True


@pytest_twisted.inlineCallbacks
def test_fake_data_delay_task(agent):
    session = create_session('delay_task')
    params = {'delay': 0.001, 'succeed': True}
    res = yield agent.delay_task(session, params=params)
    assert res[0] is True

@pytest_twisted.inlineCallbacks
def test_fake_data_delay_task_abort(agent):
    session = create_session('delay_task')
    params = {'delay': 0.001, 'succeed': True}
    D1 = agent.delay_task(session, params=params)
    D2 = yield agent._abort_delay_task(session, params=None)
    res = yield D1
    assert res[0] is False


def test_fake_data_try_set_job_running_job(agent):
    # set running job to 'acq'
    agent.job = 'acq'

    res = agent.try_set_job('not_acq')

    assert res[0] is False
