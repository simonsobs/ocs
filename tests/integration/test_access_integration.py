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

AGENT_PATH = '../ocs/agents/fake_data/agent.py'

pytest_plugins = ("docker_compose")

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    AGENT_PATH, 'fake_data', ['--access-policy', 'override:a,b'])
client_1 = create_client_fixture('fake-data-local')
client_2 = create_client_fixture('fake-data-local', privs='a')


@pytest.mark.integtest
def test_fake_data_agent_delay_task(wait_for_crossbar, run_agent,
                                    client_1, client_2):
    # Without password, start should fail immediately.
    resp = client_1.delay_task.start(delay=0.01)
    assert resp.status == ocs.ERROR

    # With password, should succeed.
    resp = client_2.delay_task(delay=0.01)
    assert resp.status == ocs.OK
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
