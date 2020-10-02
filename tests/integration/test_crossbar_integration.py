import os
import time
import pytest
import urllib.request

from urllib.error import URLError

import docker
import numpy as np

from ocs.matched_client import MatchedClient
from so3g import hk

# Set OCS_CONFIG_DIR environment variable
os.environ['OCS_CONFIG_DIR'] = "/home/koopman/git/ocs/tests/integration/"

CLIENT = docker.from_env()
pytest_plugins = ("docker_compose",)

# Fixture to wait for crossbar server to be available.
@pytest.fixture(scope="function")
def wait_for_crossbar(function_scoped_container_getter):
    """Wait for the crossbar server from docker-compose to become responsive."""
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

def restart_crossbar():
    """Restart the crossbar server and wait for it to come back online."""
    crossbar_container = CLIENT.containers.get('crossbar')
    crossbar_container.restart()

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

def test_testing(wait_for_crossbar):
    "Just testing if the docker-compose/crossbar wait fixture is working."
    assert True

def test_fake_data_after_crossbar_restart(wait_for_crossbar):
    """Restart the crossbar server, then test whether we can issue a command to
    run a task, then check the sesssion.data on the acq process to see if it's
    updating with new data.

    The task call wouldn't work if we didn't reconnect to the crossbar server,
    and the acq process should still be running.

    """
    restart_crossbar()
    now = time.time()
    # Check fake data Agent is accessible and producing new data.
    therm_client = MatchedClient('fake-data1', args=[])

    # Make sure we can call a task.
    therm_client.delay_task()
    therm_client.delay_task.wait()

    response = therm_client.acq.status()
    assert response.session.get('data').get('timestamp') > now

def test_influxdb_publisher_after_crossbar_restart(wait_for_crossbar):
    """Test that the InfluxDB publisher reconnects after a crossbar restart and
    continues to publish data to the InfluxDB.

    """
    pass

def test_aggregator_after_crossbar_restart(wait_for_crossbar):
    """Test that the aggregator reconnects after a crossbar restart and that
    data from after the reconnection makes it into the latest .g3 file.

    """
    # record first file being written by aggregator
    time.sleep(2) # give a few seconds for things to collect some data
    agg_client = MatchedClient('aggregator', args=[])
    status = agg_client.record.status()
    starting_file = status.session.get('data').get('current_file')
    assert starting_file is not None

    # restart crossbar
    restart_crossbar()

    # record current time
    now = time.time()

    # wait for file rotation by checking session.data's "current_file" value
    status = agg_client.record.status()
    current_file = status.session.get('data').get('current_file')
    iterations = 0
    while current_file == starting_file:
        time.sleep(1)
        status = agg_client.record.status()
        current_file = status.session.get('data').get('current_file')
        iterations += 1

        # setting in default.yaml is 10 second files, though 20 seconds happens
        if iterations > 25:
            raise RuntimeError(f'Aggregator file not rotating. {starting_file} == {current_file}')

    # open rotated file and see if any data after recorded time exists
    scanner = hk.HKArchiveScanner()
    scanner.process_file("." + starting_file)
    arc = scanner.finalize()
    data = arc.simple(['channel_00'])
    assert np.any(data[0][0] > now)

    # wait for another rotation and check that file?
    status = agg_client.record.status()
    next_file = status.session.get('data').get('current_file')
    iterations = 0
    while current_file == next_file:
        time.sleep(1)
        status = agg_client.record.status()
        next_file = status.session.get('data').get('current_file')
        iterations += 1

        # setting in default.yaml is 10 second files, though 20 seconds happens
        if iterations > 25:
            raise RuntimeError(f'Aggregator file not rotating. {starting_file} == {current_file}')

    # check "current_file" is not empty
    scanner = hk.HKArchiveScanner()
    scanner.process_file("." + current_file)
    arc = scanner.finalize()
    data = arc.simple(['channel_00'])
    assert data[0][0].size
