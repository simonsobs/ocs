import pytest
import time

import ocs
from ocs.base import OpCode
from ocs import access, ocs_client

from ocs.testing import (
    create_agent_runner_fixture,
    create_client_fixture,
)

from integration.util import (
    create_crossbar_fixture,
)
from integration.util import docker_compose_file  # noqa: F401


wait_for_crossbar = create_crossbar_fixture()

# For debugging.
_LOG_ARGS = []  # ["--log-dir", "./logs"]

# Tests in this module make use of two agent instances:
FAKER_ID = 'fake-data-access-dir'
ADIR_ID = 'access-dir'

FAKER_PATH = '../ocs/agents/fake_data/agent.py'
ADIR_PATH = '../ocs/agents/access_director/agent.py'


def create_fakedata_fixture(access_policy=None):
    args = ['--instance-id', FAKER_ID] + _LOG_ARGS
    if access_policy:
        args += ['--access-policy', access_policy]
    return create_agent_runner_fixture(
        FAKER_PATH, 'accessdir_override', args)


# Different ways to launch the faker.
run_fakedata_nodir = create_fakedata_fixture(access_policy='none')
run_fakedata_override = create_fakedata_fixture(access_policy='override:a,b')
run_fakedata_accessdir = create_fakedata_fixture()

# Clients to the faker.
client_no_privs = create_client_fixture(FAKER_ID)
client_bad_privs = create_client_fixture(FAKER_ID, privs='xyz')
client_good_privs = create_client_fixture(FAKER_ID, privs='a')
client_super_user = create_client_fixture(FAKER_ID, privs='superuser')

# Access Director agent and client
run_access_director = create_agent_runner_fixture(
    ADIR_PATH, ADIR_ID, _LOG_ARGS)
client_adir = create_client_fixture(ADIR_ID)


@pytest.mark.integtest
def test_access_lockout(wait_for_crossbar,
                        run_fakedata_accessdir,
                        client_good_privs):
    """Test that when an agent is told to take credentials from the
    AccessDirector, it rejects all requests if the Access Director is
    not online.

    """
    resp = client_good_privs.delay_task.start(delay=0.01)
    assert resp.status == ocs.ERROR

    resp = client_good_privs.acq.start()
    assert resp.status == ocs.ERROR


@pytest.fixture
def setup_access_system(wait_for_crossbar,
                        run_access_director,
                        run_fakedata_accessdir):
    """Launch crossbar, Access Director, and FakeData agent; wait a
    couple of seconds for them to synchronize.

    """
    time.sleep(2)


@pytest.mark.integtest
def test_access_director(setup_access_system,
                         client_good_privs,
                         client_bad_privs,
                         client_no_privs):
    """Test that agent receives credentials from Access Director and
    that the programmed passwords work.

    """
    # This should work tho...
    resp = client_bad_privs.acq.start()
    assert resp.status == ocs.OK

    # Without password, start should fail immediately.
    resp = client_no_privs.delay_task.start(delay=0.01)
    assert resp.status == ocs.ERROR

    # With password, should succeed.
    resp = client_good_privs.delay_task(delay=0.01)
    assert resp.status == ocs.OK
    time.sleep(1)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_exclusive_access(setup_access_system,
                          client_adir,
                          client_good_privs,
                          client_super_user):
    """Test that exclusive access system locks out normal clients.

    """
    # Obtain exclusive access to the "test-grant".
    eac = access.ExclusiveAccessClient(client_adir, 'test-grantee', 'test-grant')
    ok, info = eac.acquire()
    assert ok
    time.sleep(1)

    # Confirm old passwords don't work
    resp = client_good_privs.delay_task.start(delay=0.1)
    assert resp.status == ocs.ERROR

    # ... but excl-access special password works.
    client_exac = ocs_client.OCSClient(FAKER_ID, privs=info['password'])
    resp = client_exac.delay_task.start(delay=0.01)
    assert resp.status == ocs.OK
    client_exac.delay_task.wait()

    # ... and super-user still works.
    resp = client_super_user.delay_task.start(delay=0.01)
    assert resp.status == ocs.OK
    client_super_user.delay_task.wait()

    # Release the lock.
    ok, info = eac.release()
    assert ok
    time.sleep(1)

    # And confirm old behavior.
    resp = client_good_privs.delay_task.start(delay=0.1)
    assert resp.status == ocs.OK
    client_good_privs.delay_task.wait()
