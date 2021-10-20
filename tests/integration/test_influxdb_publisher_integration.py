import pytest

import ocs
from ocs.base import OpCode

from integration.util import (
    create_agent_runner_fixture,
    create_client_fixture,
    create_crossbar_fixture
)

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    '../agents/influxdb_publisher/influxdb_publisher.py',
    'influxagent-local')
client = create_client_fixture('influxagent-local')


@pytest.mark.integtest
def test_influxdb_publisher_agent_record(wait_for_crossbar, run_agent, client):
    resp = client.record.start(run_once=True)
    print(resp)
    assert resp.status == ocs.OK

    resp = client.record.wait(timeout=20)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
