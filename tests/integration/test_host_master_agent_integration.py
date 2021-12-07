import os
import pytest

from ocs.base import OpCode

from integration.util import (
    create_agent_runner_fixture,
    create_client_fixture,
    create_crossbar_fixture
)

pytest_plugins = ("docker_compose")


wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture('../agents/host_manager/host_manager.py',
                                        'host-manager-1',
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])
client = create_client_fixture('host-manager-1', timeout=5)


@pytest.mark.integtest
def test_host_manager_agent_manager(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.manager.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value
