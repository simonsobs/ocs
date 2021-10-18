import os
import pytest

from ocs.matched_client import MatchedClient

# so we need a unique util name, or to put them all in the same place, probably
# a directory up, or perhaps in the package itself
from util2 import create_agent_runner_fixture, create_crossbar_fixture

from ocs.base import OpCode

pytest_plugins = ("docker_compose")


wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture('../agents/registry/registry.py',
                                        'registry',
                                        startup_sleep=2,
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    client = MatchedClient('registry')
    return client


@pytest.mark.integtest
def test_registry_agent_main(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.main.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value

    # Request main to stop
    client.main.stop()
    resp = client.main.status()
    assert resp.session['op_code'] == OpCode.STOPPING.value
