import os
import time
import pytest
import signal
import subprocess
import coverage.data
import urllib.request
import docker

from urllib.error import URLError

from ocs.matched_client import MatchedClient


def create_agent_runner_fixture(agent_path, agent_name, startup_sleep=1, args=None):
    """Create a pytest fixture for running a given OCS Agent.

    Parameters:
        agent_path (str): Relative path to Agent,
            i.e. '../agents/fake_data/fake_data_agent.py'
        agent_name (str): Short, unique name for the agent
        startup_sleep (int): Seconds to wait after Agent startup before
            commands can be sent. If the Client can't find the registered
            Agent, try increasing this gradually.
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

        # wait for Agent to connect
        time.sleep(startup_sleep)

        yield

        # shutdown Agent
        agentproc.send_signal(signal.SIGINT)
        time.sleep(1)

        # report coverage
        agentcov = coverage.data.CoverageData(
            basename=f'.coverage.agent.{agent_name}')
        agentcov.read()
        cov.get_data().update(agentcov)

    return run_agent


def _check_crossbar_connection():
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


def create_crossbar_fixture():
    # Fixture to wait for crossbar server to be available.
    # Speeds up tests a bit to have this session scoped
    # If tests start interfering with one another this should be changed to
    # "function" scoped and session_scoped_container_getter should be changed to
    # function_scoped_container_getter
    # @pytest.fixture(scope="session")
    # def wait_for_crossbar(session_scoped_container_getter):
    @pytest.fixture(scope="function")
    def wait_for_crossbar(function_scoped_container_getter):
        """Wait for the crossbar server from docker-compose to become
        responsive.

        """
        _check_crossbar_connection()

    return wait_for_crossbar


def restart_crossbar():
    """Restart the crossbar server and wait for it to come back online."""
    client = docker.from_env()
    crossbar_container = client.containers.get('crossbar')
    crossbar_container.restart()
    _check_crossbar_connection()


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
                client = MatchedClient(instance_id)
                break
            except RuntimeError as e:
                print(f"Caught error: {e}")
                print("Attempting to reconnect.")

            time.sleep(1)
            attempts += 1

        return client

    return client_fixture
