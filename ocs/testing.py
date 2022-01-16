import os
import time
import pytest
import signal
import subprocess
import coverage.data
import urllib.request
import docker

from urllib.error import URLError

from ocs.ocs_client import OCSClient


def create_agent_runner_fixture(agent_path, agent_name, args=None):
    """Create a pytest fixture for running a given OCS Agent.

    Parameters:
        agent_path (str): Relative path to Agent,
            i.e. '../agents/fake_data/fake_data_agent.py'
        agent_name (str): Short, unique name for the agent
        args (list): Additional CLI arguments to add when starting the Agent

    """
    @pytest.fixture()
    def run_agent(cov):
        env = os.environ.copy()
        env['COVERAGE_FILE'] = f'.coverage.agent.{agent_name}'
        env['OCS_CONFIG_DIR'] = os.getcwd()
        cmd = ['coverage', 'run',
               '--rcfile=./.coveragerc',
               agent_path,
               '--site-file',
               './default.yaml']
        if args is not None:
            cmd.extend(args)
        agentproc = subprocess.Popen(cmd,
                                     env=env,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     preexec_fn=os.setsid)

        # wait for Agent to startup 
        time.sleep(1)

        yield

        # shutdown Agent
        agentproc.send_signal(signal.SIGINT)
        time.sleep(1)

        # report coverage
        agentcov = coverage.data.CoverageData(
            basename=f'.coverage.agent.{agent_name}')
        agentcov.read()
        # protect against missing --cov flag
        if cov is not None:
            cov.get_data().update(agentcov)

    return run_agent


def create_client_fixture(instance_id, timeout=30):
    """Create the fixture that provides tests a Client object.

    Parameters:
        instance_id (str): Agent instance-id to connect the Client to
        timeout (int): Approximate timeout in seconds for the connection.
            Connection attempts will be made X times, with a 1 second pause
            between attempts. This is useful if it takes some time for the
            Agent to start accepting connections, which varies depending on the
            Agent.

    """
    @pytest.fixture()
    def client_fixture():
        # Set the OCS_CONFIG_DIR so we read the local default.yaml file
        os.environ['OCS_CONFIG_DIR'] = os.getcwd()
        print(os.environ['OCS_CONFIG_DIR'])
        attempts = 0

        while attempts < timeout:
            try:
                client = OCSClient(instance_id)
                break
            except RuntimeError as e:
                print(f"Caught error: {e}")
                print("Attempting to reconnect.")

            time.sleep(1)
            attempts += 1

        return client

    return client_fixture


def check_crossbar_connection(port=18001, interval=5, max_attempts=6):
    """Check that the crossbar server is up and available for an Agent to
    connect to.

    Parameters:
        port (int): Port the crossbar server is configured to run on for
            testing.
        interval (float): Amount of time in seconds to wait between checks.
        max_attempts (int): Maximum number of attempts before giving up.

    Notes:
        For this check to work the crossbar server needs the `Node Info Service
        <https://crossbar.io/docs/Node-Info-Service/>`_ running at the path /info.


    """
    attempts = 0

    while attempts < max_attempts:
        try:
            code = urllib.request.urlopen(f"http://localhost:{port}/info").getcode()
        except (URLError, ConnectionResetError):
            print("Crossbar server not online yet, waiting 5 seconds.")
            time.sleep(interval)

        attempts += 1

    assert code == 200
    print("Crossbar server online.")
