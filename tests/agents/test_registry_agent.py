import time
import pytest_twisted

from agents.util import create_session, create_agent_fixture

from ocs.agents.registry.agent import Registry

agent = create_agent_fixture(Registry)


class TestMain:
    @pytest_twisted.inlineCallbacks
    def test_registry_main(self, agent):
        session = create_session('main')

        # Fake a heartbeat by directly registering an Agent
        # op_codes, feed
        op_codes = {'operation1': 5, 'operation2': 1}
        heartbeat_example = [op_codes,
                             {"agent_address": "observatory.test_agent",
                              "agg_params": {},
                              "feed_name": "heartbeat",
                              "address": "observatory.test_agent.feeds.heartbeat",
                              "record": False,
                              "session_id": str(time.time())}]
        agent._register_heartbeat(heartbeat_example)

        params = {'test_mode': True}
        res = yield agent.main(session, params)

        assert res[0] is True

        assert 'observatory.test_agent' in session.data
        assert session.data['observatory.test_agent']['expired'] is False
        assert session.data['observatory.test_agent']['time_expired'] is None
        assert session.data['observatory.test_agent']['op_codes'] == op_codes

    @pytest_twisted.inlineCallbacks
    def test_registry_main_expire_agent(self, agent):
        session = create_session('main')

        # Fake a heartbeat by directly registering an Agent
        # op_codes, feed
        op_codes = {'operation1': 5, 'operation2': 1}
        heartbeat_example = [op_codes,
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

        params = {'test_mode': True}
        res = yield agent.main(session, params)

        assert agent.registered_agents['observatory.test_agent'].expired is True
        assert res[0] is True

        assert 'observatory.test_agent' in session.data
        assert session.data['observatory.test_agent']['expired'] is True
        assert session.data['observatory.test_agent']['time_expired'] is not None
        expected_op_codes = {'operation1': 7, 'operation2': 7}
        assert session.data['observatory.test_agent']['op_codes'] == expected_op_codes


class TestStopMain:
    @pytest_twisted.inlineCallbacks
    def test_registry_stop_main_while_running(self, agent):
        session = create_session('main')

        # Fake run main process
        agent._run = True

        res = yield agent._stop_main(session, params=None)
        assert res[0] is True

    @pytest_twisted.inlineCallbacks
    def test_registry_stop_main_not_running(self, agent):
        session = create_session('main')
        res = yield agent._stop_main(session, params=None)
        assert res[0] is False


def test_registry_register_agent(agent):
    session = create_session('main')
    agent_data = {'agent_address': 'observatory.test_agent'}
    res = agent._register_agent(session, agent_data)
    assert res[0] is True
