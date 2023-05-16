import time
import pytest_twisted

from agents.util import create_session, create_agent_fixture

from ocs.agents.registry.agent import RegisteredAgent, Registry, make_parser
from ocs import site_config

parser = make_parser()
site_config.add_arguments(parser)
args = parser.parse_args(['--wait-time', '0.1'])
agent = create_agent_fixture(Registry, agent_kwargs=dict(args=args))


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


def test_registry_handles_changed_agent_ops(agent):
    """If an agent's op_codes change while the registry is running, for
    instance an operation is added, this causes an exception to be raised, as
    the Block structure has changed, which is disallowed. See [1] or [2].

    [1] - https://github.com/simonsobs/ocs/issues/254
    [2] - https://github.com/simonsobs/ocs/issues/311

    """
    # Only need 'agent_address' and 'op_codes' attributes for test
    feed = {'agent_address': 'observatory.registry',
            'agg_params': None,
            'feed_name': 'test',
            'address': None,
            'record': True,
            'session_id': None,
            'agent_class': 'Registry'}
    reg_agent = RegisteredAgent(feed)
    reg_agent.op_codes = {'op_name': 1}

    agent._publish_agent_ops(reg_agent)

    # Add a new op to the registered agent
    reg_agent.op_codes = {'op_name': 1, 'new_op': 1}
    agent._publish_agent_ops(reg_agent)
