import os
import time
import pytest

import docker

from ocs.ocs_client import OCSClient
from so3g import hk

from integration.util import create_crossbar_fixture, restart_crossbar
from integration.util import docker_compose_file  # noqa: F401

wait_for_crossbar = create_crossbar_fixture()


CROSSBAR_SLEEP = 5  # time to wait before trying to make first connection


# @pytest.mark.integtest
# def test_testing(wait_for_crossbar):
#     "Just testing if the docker-compose/crossbar wait fixture is working."
#     assert True

@pytest.mark.integtest
def test_fake_data_after_crossbar_restart(wait_for_crossbar):
    """Restart the crossbar server, then test whether we can issue a command to
    run a task, then check the sesssion.data on the acq process to see if it's
    updating with new data.

    The task call wouldn't work if we didn't reconnect to the crossbar server,
    and the acq process should still be running.

    """
    # give a few seconds for things to make first connection
    time.sleep(CROSSBAR_SLEEP)
    restart_crossbar()
    now = time.time()

    # Set OCS_CONFIG_DIR environment variable
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()

    # Check fake data Agent is accessible and producing new data.
    therm_client = OCSClient('fake-data1', args=[])

    # Make sure we can call a task.
    therm_client.delay_task()
    therm_client.delay_task.wait()

    response = therm_client.acq.status()
    assert response.session.get('data').get('timestamp') > now

# @pytest.mark.integtest
# def test_influxdb_publisher_after_crossbar_restart(wait_for_crossbar):
#     """Test that the InfluxDB publisher reconnects after a crossbar restart and
#     continues to publish data to the InfluxDB.
#
#     """
#     pass


@pytest.mark.integtest
def test_aggregator_after_crossbar_restart(wait_for_crossbar):
    """Test that the aggregator reconnects after a crossbar restart and that
    data from after the reconnection makes it into the latest .g3 file.

    """
    # Set OCS_CONFIG_DIR environment variable
    os.environ['OCS_CONFIG_DIR'] = os.getcwd()

    # record first file being written by aggregator
    # give a few seconds for things to make first connection
    time.sleep(CROSSBAR_SLEEP)
    agg_client = OCSClient('aggregator', args=[])
    status = agg_client.record.status()
    file00 = status.session.get('data').get('current_file')
    assert file00 is not None

    # restart crossbar
    restart_crossbar()

    # record current time
    # now = time.time()

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
    data = arc.simple(all_fields)  # noqa: F841 -- since used in commented section below

    # Check for gaps in all timestreams
    # This is an unreliable assertion
    # for i, dataset in enumerate(data):
    #    assert np.all(np.diff(dataset[0]) < 0.25), f"{all_fields[i]} contains gap in data larger than 0.25 seconds"


@pytest.mark.integtest
def test_proper_agent_shutdown_on_lost_transport(wait_for_crossbar):
    """If the crossbar server goes down, i.e. TransportLost, after the timeout
    period an Agent should shutdown after the reactor.stop() call. This will mean
    the container running the Agent is gone.

    Startup everything. Shutdown the crossbar server. Check for fake data agent
    container. It's gotta be gone for a pass.

    """
    client = docker.from_env()

    # give a few seconds for things to make first connection
    time.sleep(CROSSBAR_SLEEP)

    # shutdown crossbar
    crossbar_container = client.containers.get('ocs-tests-crossbar')
    crossbar_container.stop()

    # 15 seconds should be enough with default 10 second timeout
    timeout = 25
    while timeout > 0:
        time.sleep(1)  # give time for the fake-data-agent to timeout, then shutdown
        fake_data_container = client.containers.get('ocs-tests-fake-data-agent')
        if fake_data_container.status == "exited":
            break
        timeout -= 1

    fake_data_container = client.containers.get('ocs-tests-fake-data-agent')
    assert fake_data_container.status == "exited"

    # Restart crossbar, else docker plugin loses track of it
    crossbar_container.start()
