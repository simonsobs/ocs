import os
import time
import pytest
import signal
import subprocess
import coverage.data
import urllib.request

from urllib.error import URLError

from ocs.matched_client import MatchedClient

# trying to figure out good organization for helper functions/etc.
# this can be imported when pytest is run for all tests in the above directory
# but can't be imported if you do something like:
# $ python3 -m pytest --cov --cov-report=html -k 'test_fake_data_delay' integration/test_fake_data_agent_integration.py
# which makes sense to me
# it doesn't quite make sense to me why this is importable otherwise
# that also causes a conflict, say if we had a util.py in each test directory,
# they will be in the same namespace when going to import, which isn't good
# from util import create_session

# so we need a unique util name, or to put them all in the same place, probably
# a directory up, or perhaps in the package itself
from util2 import create_agent_runner_fixture

import ocs
from ocs.base import OpCode

pytest_plugins = ("docker_compose")

# Set the OCS_CONFIG_DIR so we read the local default.yaml file always
os.environ['OCS_CONFIG_DIR'] = os.getcwd()


# Fixture to wait for crossbar server to be available.
# Speeds up tests a bit to have this session scoped
# If tests start interfering with one another this should be changed to
# "function" scoped and session_scoped_container_getter should be changed to
# function_scoped_container_getter
@pytest.fixture(scope="session")
def wait_for_crossbar(session_scoped_container_getter):
    """Wait for the crossbar server from docker-compose to become
    responsive.

    """
    attempts = 0

    while attempts < 6:
        try:
            code = urllib.request.urlopen("http://localhost:8001/info").getcode()
        except (URLError, ConnectionResetError):
            print("Crossbar server not online yet, waiting 5 seconds.")
            time.sleep(5)

        attempts += 1

    assert code == 200
    print("Crossbar server online.")

run_fake_data_agent = create_agent_runner_fixture('../agents/fake_data/fake_data_agent.py', 'fake_data')

@pytest.fixture()
def client():
    client = MatchedClient('fake-data1')
    return client


@pytest.mark.integtest
def test_fake_data_delay_task_int(wait_for_crossbar, run_fake_data_agent, client):
    resp = client.delay_task(delay=0.01)
    print(resp)
    assert resp.status == ocs.OK
    print(resp.session)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


@pytest.mark.integtest
def test_fake_data_set_heartbeat_int(wait_for_crossbar, run_fake_data_agent, client):
    resp = client.set_heartbeat(heartbeat=True)
    print(resp)
    assert resp.status == ocs.OK
    print(resp.session)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
