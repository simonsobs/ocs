import os
import time
import pytest

from ocs.base import OpCode
from ocs import ocsbow


from ocs.testing import (
    create_agent_runner_fixture,
    create_client_fixture,
)

from integration.util import (
    create_crossbar_fixture
)

pytest_plugins = ("docker_compose")


wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture('../ocs/agents/host_manager/agent.py',
                                        'host-manager-1',
                                        args=['--log-dir',
                                              os.path.join(os.getcwd(),
                                                           'log/')])
client = create_client_fixture('host-manager-1', timeout=5)


@pytest.mark.integtest
def test_host_manager_agent_manager(wait_for_crossbar, run_agent, client):
    # Startup is always true, so let's check it's running
    resp = client.manager.status()
    print(resp)
    assert resp.session['op_code'] == OpCode.RUNNING.value

    def find_child(resp, instance_id):
        for v in resp.session['data']['child_states']:
            if v['instance_id'] == instance_id:
                return v
        raise ValueError

    target = 'fake-data-local'

    state = find_child(resp, target)
    assert(state['target_state'] == 'down')
    assert(state['next_action'] == 'down')

    # Start it up
    resp = client.update(requests=[(target, 'up')])
    print(resp)

    # Give manager session data a chance to update
    for i in range(10):
        time.sleep(1)
        resp = client.manager.status()
        state = find_child(resp, target)
        if state['target_state'] == 'up':
            break
    else:
        raise RuntimeError("state['target_state'] != 'up'")

    # Check ocsbow
    ocsbow.main(['status'])
    ocsbow.main(['up', target])
    ocsbow.main(['down', 'host-manager-1'])
