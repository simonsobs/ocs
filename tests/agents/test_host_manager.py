import sys
sys.path.insert(0, '../agents/host_manager/')
from host_manager import HostManager

from agents.util import create_session, create_agent_fixture


# fixtures
agent = create_agent_fixture(HostManager)


def test_host_manager_update_not_running(agent):
    session = create_session('update')
    res = agent.update(session, params=None)
    assert res[0] is False
