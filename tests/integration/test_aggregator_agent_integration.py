import os
import pytest

from ocs.matched_client import MatchedClient

# so we need a unique util name, or to put them all in the same place, probably
# a directory up, or perhaps in the package itself
from util2 import create_agent_runner_fixture, create_crossbar_fixture

import ocs
from ocs.base import OpCode

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    '../agents/aggregator/aggregator_agent.py',
    'aggregator-local',
    startup_sleep=2)


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    print(os.environ['OCS_CONFIG_DIR'])
    client = MatchedClient('aggregator-local')
    return client


@pytest.mark.integtest
def test_aggregator_agent_record(wait_for_crossbar, run_agent, client):
    resp = client.record.start(run_once=True)
    print(resp)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.STARTING.value

    # We stopped the process with run_once=True, but that will leave us in the
    # RUNNING state
    resp = client.record.status()
    assert resp.session['op_code'] == OpCode.RUNNING.value

    # Startup is always true, so let's stop record first
    client.record.stop()
    resp = client.record.status()
    assert resp.session['op_code'] == OpCode.STOPPING.value
