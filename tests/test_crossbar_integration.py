import os
import time
import pytest
import urllib.request

from urllib.error import URLError

import docker
import numpy as np

from ocs.matched_client import MatchedClient

try:
    from so3g import hk
except ModuleNotFoundError as e:
    print(f"Unable to import so3g: {e}")

# Set OCS_CONFIG_DIR environment variable
os.environ['OCS_CONFIG_DIR'] = os.getcwd()

pytest_plugins = ("docker_compose",)

@pytest.mark.dependency(name="so3g")
def test_so3g_spt3g_import():
    """Test that we can import so3g. Used to skip tests dependent on
    this import.

    """
    import so3g

    # Just to prevent flake8 from complaining
    print(so3g.__file__)

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
    client = docker.from_env()
    crossbar_container = client.containers.get('crossbar')
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

@pytest.mark.integtest
def test_testing(wait_for_crossbar):
    "Just testing if the docker-compose/crossbar wait fixture is working."
    assert True

@pytest.mark.integtest
def test_fake_data_after_crossbar_restart(wait_for_crossbar):
    """Restart the crossbar server, then test whether we can issue a command to
    run a task, then check the sesssion.data on the acq process to see if it's
    updating with new data.

    The task call wouldn't work if we didn't reconnect to the crossbar server,
    and the acq process should still be running.

    """
    time.sleep(5) # give a few seconds for things to make first connection
    restart_crossbar()
    now = time.time()
    # Check fake data Agent is accessible and producing new data.
    therm_client = MatchedClient('fake-data1', args=[])

    # Make sure we can call a task.
    therm_client.delay_task()
    therm_client.delay_task.wait()

    response = therm_client.acq.status()
    assert response.session.get('data').get('timestamp') > now

@pytest.mark.integtest
def test_influxdb_publisher_after_crossbar_restart(wait_for_crossbar):
    """Test that the InfluxDB publisher reconnects after a crossbar restart and
    continues to publish data to the InfluxDB.

    """
    pass

@pytest.mark.dependency(depends=["so3g"])
@pytest.mark.integtest
def test_aggregator_after_crossbar_restart(wait_for_crossbar):
    """Test that the aggregator reconnects after a crossbar restart and that
    data from after the reconnection makes it into the latest .g3 file.

    """
    # record first file being written by aggregator
    time.sleep(5) # give a few seconds for things to collect some data
    agg_client = MatchedClient('aggregator', args=[])
    status = agg_client.record.status()
    file00 = status.session.get('data').get('current_file')
    assert file00 is not None

    # restart crossbar
    restart_crossbar()

    # record current time
    now = time.time()

    # wait for file rotation by checking session.data's "current_file" value
    status = agg_client.record.status()
    file01 = status.session.get('data').get('current_file')
    iterations = 0
    while file01 == file00:
        time.sleep(1)
        status = agg_client.record.status()
        file01 = status.session.get('data').get('current_file')
        iterations += 1

        # setting in default.yaml is 30 second files, though 40 seconds happens
        if iterations > 45:
            raise RuntimeError(f'Aggregator file not rotating. {file00} == {file01}')

    # open rotated file and see if any data after recorded time exists
    # scanner = hk.HKArchiveScanner()
    # scanner.process_file("." + file00)
    # arc = scanner.finalize()
    # data = arc.simple(['channel_00'])
    # assert np.any(data[0][0] > now)

    # wait for another rotation and check that file?
    status = agg_client.record.status()
    file02 = status.session.get('data').get('current_file')
    iterations = 0
    while file01 == file02:
        time.sleep(1)
        status = agg_client.record.status()
        file02 = status.session.get('data').get('current_file')
        iterations += 1

        # setting in default.yaml is 30 second files, though 40 seconds happens
        if iterations > 45:
            raise RuntimeError(f'Aggregator file not rotating. {file01} == {file02}')

    # check "file01" is not empty
    # scanner = hk.HKArchiveScanner()
    # scanner.process_file("." + file01)
    # arc = scanner.finalize()
    # data = arc.simple(['channel_00'])
    # assert data[0][0].size

    # Perhaps the best test of whether we've lost data is to see if there are
    # gaps between datapoints

    # Open all created files and make sure no gaps
    scanner = hk.HKArchiveScanner()
    files = [file00, file01, file02]
    for f in files:
        scanner.process_file("." + f)
    arc = scanner.finalize()

    # Get all fields in the file
    all_fields = []
    for k, v in arc.get_fields()[0].items():
        all_fields.append(k)
    data = arc.simple(all_fields)

    # Check for gaps in all timestreams
    for i, dataset in enumerate(data):
        assert np.all(np.diff(dataset[0]) < 0.25), f"{all_fields[i]} contains gap in data larger than 0.25 seconds"

@pytest.mark.integtest
def test_proper_agent_shutdown_on_lost_transport(wait_for_crossbar):
    """If the crossbar server goes down, i.e. TransportLost, after the timeout
    period an Agent should shutdown after the reactor.stop() call. This will mean
    the container running the Agent is gone.

    Startup everything. Shutdown the crossbar server. Check for fake data agent
    container. It's gotta be gone for a pass.

    """
    client = docker.from_env()

    time.sleep(5) # give a few seconds for things to make first connection

    # shutdown crossbar
    crossbar_container = client.containers.get('crossbar')
    crossbar_container.stop()

    # 15 seconds should be enough with default 10 second timeout
    timeout = 15
    while timeout > 0:
        time.sleep(1) # give time for the fake-data-agent to timeout, then shutdown
        fake_data_container = client.containers.get('fake-data-agent')
        if fake_data_container.status == "exited":
            break
        timeout -= 1

    fake_data_container = client.containers.get('fake-data-agent')
    assert fake_data_container.status == "exited"
