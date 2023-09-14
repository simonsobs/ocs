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
from integration.util import docker_compose_file  # noqa: F401

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

    # Check whether managed agents are getting to their requested
    # initial state.  The expectations here are matched to manage:
    # settings in default.yaml.  We check the "up" ones first, because
    # once we've waited for those to come up we've probably waited
    # long enough to ensure the 'down' ones aren't going to also come
    # up unexpectedly.

    timeout = time.time() + 10
    for target, is_managed, init_state in [
            ('registry', True, 'up'),
            ('influxagent-local', True, 'up'),
            ('fake-data-local', True, 'down'),
            ('aggregator-local', False, None),
    ]:
        print(f'Waiting for {target} ...')
        if is_managed:
            while time.time() < timeout:
                resp = client.manager.status()
                state = find_child(resp, target)
                if state['next_action'] == init_state:
                    break
                time.sleep(.5)
            assert state['target_state'] == init_state
        else:
            with pytest.raises(ValueError):
                state = find_child(resp, target)

    # Start it up
    target = 'fake-data-local'
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
