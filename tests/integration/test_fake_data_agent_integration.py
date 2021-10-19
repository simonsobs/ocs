import os
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
run_fake_data_agent = create_agent_runner_fixture(
    '../agents/fake_data/fake_data_agent.py', 'fake_data')


@pytest.fixture()
def client():
    # Set the OCS_CONFIG_DIR so we read the local default.yaml file always
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()
    client = MatchedClient('fake-data2')
    return client


@pytest.mark.integtest
def test_fake_data_agent_delay_task(wait_for_crossbar, run_fake_data_agent, client):
    resp = client.delay_task(delay=0.01)
    # print(resp)
    assert resp.status == ocs.OK
    # print(resp.session)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_fake_data_agent_set_heartbeat(wait_for_crossbar, run_fake_data_agent, client):
    resp = client.set_heartbeat(heartbeat=True)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_fake_data_agent_acq(wait_for_crossbar, run_fake_data_agent, client):
    resp = client.acq.start(run_once=True)
    print(resp)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.STARTING.value

    # We stopped the process with run_once=True, but that will leave us in the
    # RUNNING state
    resp = client.acq.status()
    assert resp.session['op_code'] == OpCode.RUNNING.value

    # Now we request a formal stop, which should put us in STOPPING
    client.acq.stop()
    resp = client.acq.status()
    assert resp.session['op_code'] == OpCode.STOPPING.value


# Test autostartup
run_fake_data_agent_acq = create_agent_runner_fixture('../agents/fake_data/fake_data_agent.py', 'fake_data', args=['--mode', 'acq'])


@pytest.mark.integtest
def test_fake_data_agent_delay_task_autostartup(wait_for_crossbar, run_fake_data_agent_acq, client):
    resp = client.delay_task(delay=0.01)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
