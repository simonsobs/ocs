from ocs.agents.host_manager import HostManager

import pytest_twisted

from agents.util import create_session, create_agent_fixture


# fixtures
agent = create_agent_fixture(HostManager)


@pytest_twisted.inlineCallbacks
def test_host_manager_update_not_running(agent):
    session = create_session('update')
    res = yield agent.update(session, params=None)
    assert res[0] is False
