import os
import pytest

from ocs.matched_client import MatchedClient

from integration.util import (
    create_agent_runner_fixture,
    create_crossbar_fixture
)

from ocs.base import OpCode

pytest_plugins = ("docker_compose")


wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture('../agents/host_master/host_master.py',
                                        'master-host-1',
                                        startup_sleep=2,
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    client = MatchedClient('master-host-1')
    return client


@pytest.mark.integtest
def test_host_master_agent_master(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.master.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value
