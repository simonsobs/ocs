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
run_agent = create_agent_runner_fixture('../agents/host_master/host_master.py',
                                        'master-host-1',
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])
client = create_client_fixture('master-host-1')


@pytest.mark.integtest
def test_host_master_agent_master(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.master.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value
