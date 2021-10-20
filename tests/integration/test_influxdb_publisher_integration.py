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
    '../agents/influxdb_publisher/influxdb_publisher.py',
    'influxagent-local',
    startup_sleep=2)


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    print(os.environ['OCS_CONFIG_DIR'])
    client = MatchedClient('influxagent-local')
    return client


@pytest.mark.integtest
def test_influxdb_publisher_agent_record(wait_for_crossbar, run_agent, client):
    resp = client.record.start(run_once=True)
    print(resp)
    assert resp.status == ocs.OK

    resp = client.record.wait(timeout=20)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
