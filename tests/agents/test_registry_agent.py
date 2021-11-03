import sys
sys.path.insert(0, '../agents/registry/')

import time
import pytest
import pytest_twisted

from util import create_session, create_agent_fixture


try:
    # depends on spt3g
    from registry import Registry

    agent = create_agent_fixture(Registry)
except ModuleNotFoundError as e:
    print(f"Unable to import: {e}")


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
class TestMain:
    @pytest_twisted.inlineCallbacks
    def test_registry_main(self, agent):
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

        params = {'test_mode': True}
        res = yield agent.main(session, params)

        assert res[0] is True

    @pytest_twisted.inlineCallbacks
    def test_registry_main_expire_agent(self, agent):
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

        params = {'test_mode': True}
        res = yield agent.main(session, params)

        assert agent.registered_agents['observatory.test_agent'].expired is True
        assert res[0] is True


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
class TestStopMain:
    def test_registry_stop_main_while_running(self, agent):
        session = create_session('main')

        # Fake run main process
        agent._run = True

        res = agent._stop_main(session, params=None)
        assert res[0] is True

    def test_registry_stop_main_not_running(self, agent):
        session = create_session('main')
        res = agent._stop_main(session, params=None)
        assert res[0] is False


@pytest.mark.spt3g
@pytest.mark.dependency(depends=['so3g'], scope='session')
def test_registry_register_agent(agent):
    session = create_session('main')
    agent_data = {'agent_address': 'observatory.test_agent'}
    res = agent._register_agent(session, agent_data)
    assert res[0] is True
