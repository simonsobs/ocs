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
    startup_sleep=2)


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
    assert resp.status == ocs.OK

    resp = client.record.wait(timeout=20)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
