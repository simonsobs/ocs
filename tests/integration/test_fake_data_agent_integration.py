import pytest

import ocs
from ocs.base import OpCode

from ocs.testing import (
    create_agent_runner_fixture,
    create_client_fixture,
)

from integration.util import (
    create_crossbar_fixture,
)

AGENT_PATH = '../ocs/agents/fake_data_agent.py'

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    AGENT_PATH, 'fake_data')
client = create_client_fixture('fake-data-local')


@pytest.mark.integtest
def test_fake_data_agent_delay_task(wait_for_crossbar, run_agent, client):
    resp = client.delay_task(delay=0.01)
    # print(resp)
    assert resp.status == ocs.OK
    # print(resp.session)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_fake_data_agent_set_heartbeat(wait_for_crossbar, run_agent, client):
    resp = client.set_heartbeat(heartbeat=True)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_fake_data_agent_acq(wait_for_crossbar, run_agent, client):
    resp = client.acq.start(test_mode=True)
    assert resp.status == ocs.OK

    resp = client.acq.wait(timeout=20)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


# Test autostartup
run_agent_acq = create_agent_runner_fixture(
    AGENT_PATH,
    'fake_data',
    args=['--mode', 'acq'])


@pytest.mark.integtest
def test_fake_data_agent_delay_task_autostartup(wait_for_crossbar,
                                                run_agent_acq, client):
    resp = client.delay_task(delay=0.01)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
