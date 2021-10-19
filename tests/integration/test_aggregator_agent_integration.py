import os
import time
import pytest

from ocs.matched_client import MatchedClient

from integration.util import (
    create_agent_runner_fixture,
    create_crossbar_fixture
)

import ocs
from ocs.base import OpCode

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    '../agents/aggregator/aggregator_agent.py',
    'aggregator-local',
    startup_sleep=10)


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    print(os.environ['OCS_CONFIG_DIR'])
    attempts = 0

    while attempts < 60:
        try:
            client = MatchedClient('aggregator-local')
            break
        except RuntimeError as e:
            print(f"Caught error: {e}")
            print("Attempting to reconnect.")

        time.sleep(1)
        attempts += 1

    return client


@pytest.mark.dependency(depends=["so3g"])
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
    assert resp.session['op_code'] in [OpCode.STOPPING.value, OpCode.SUCCEEDED.value]
