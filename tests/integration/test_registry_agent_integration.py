import os
import pytest

from integration.util import (
    create_agent_runner_fixture,
    create_client_fixture,
    create_crossbar_fixture
)

from ocs.base import OpCode

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture('../agents/registry/registry.py',
                                        'registry',
                                        startup_sleep=2,
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])
client = create_client_fixture('registry')


@pytest.mark.dependency(depends=["so3g"], scope='session')
@pytest.mark.integtest
def test_registry_agent_main(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.main.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value

    client.main.stop()
    resp = client.main.status()
    assert resp.session['op_code'] == OpCode.STOPPING.value
