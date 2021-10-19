import sys
sys.path.insert(0, '../agents/host_master/')
from host_master import HostMaster

from agents.util import create_session, create_agent_fixture


# fixtures
agent = create_agent_fixture(HostMaster)


def test_host_master_update_not_running(agent):
    session = create_session('update')
    res = agent.update(session, params=None)
    assert res[0] is False
