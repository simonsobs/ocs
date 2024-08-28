import os
import time
import pytest
import signal
import subprocess
import coverage.data
import urllib.request

from threading import Timer
from urllib.error import URLError

from ocs.ocs_client import OCSClient


SIGINT_TIMEOUT = 10


class _AgentRunner:
    """Class to manage running an agent as a subprocess during testing.

    Parameters:
        agent_path (str): Relative path to Agent,
            i.e. '../agents/fake_data/fake_data_agent.py'
        agent_name (str): Short, unique name for the agent
        args (list): Additional CLI arguments to add when starting the Agent

    """

    def __init__(self, agent_path, agent_name, args):
        self.env = os.environ.copy()
        self.env['COVERAGE_FILE'] = f'.coverage.agent.{agent_name}'
        self.env['OCS_CONFIG_DIR'] = os.getcwd()
        self.cmd = [
            'python',
            '-u',
            '-m',
            'coverage',
            'run',
            '--rcfile=./.coveragerc',
            agent_path,
            '--site-file',
            './default.yaml'
        ]
        if args is not None:
            self.cmd.extend(args)
        self.agent_name = agent_name
        self.proc = None
        self._timer = None
        self._timedout = False

    def run(self, timeout):
        """Run the agent subprocess.

        This runs the agent subprocess defined by ``self.cmd``. Output is
        written to a ``PIPE``. If the agent does not exit within the given
        timeout it will be interrupted with a ``SIGKILL``.

        Parameters:
            timeout (float): Timeout in seconds to wait for agent to exit.

        """
        self.proc = subprocess.Popen(self.cmd,
                                     env=self.env,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     text=True,
                                     preexec_fn=os.setsid)

        # start timer for if agent crashes and hangs
        self._timer = Timer(timeout, self._interrupt)
        self._timer.start()

        # Wait briefly then make sure subprocess hasn't already exited.
        time.sleep(1)
        if self.proc.poll() is not None:
            self._timer.cancel()
            self._raise_subprocess(f"Agent failed to startup, cmd: {self.cmd}")

    def _interrupt(self):
        # not graceful, but handles really misbehaved agent subprocesses
        self.proc.send_signal(signal.SIGKILL)
        self._timedout = True

    def _raise_subprocess(self, msg):
        stdout, stderr = self.proc.stdout.read(), self.proc.stderr.read()
        print(f'Here is stdout from {self.agent_name}:\n{stdout}')
        print(f'Here is stderr from {self.agent_name}:\n{stderr}')
        raise RuntimeError(msg)

    def shutdown(self):
        """Shutdown the agent process.

        If the agent does not respond to a ``SIGINT`` then output is printed,
        and an exception raised.

        """
        # don't send SIGINT if we've already sent SIGKILL
        if not self._timedout:
            self.proc.send_signal(signal.SIGINT)
        self._timer.cancel()

        try:
            self.proc.communicate(timeout=SIGINT_TIMEOUT)
        except subprocess.TimeoutExpired:
            self._raise_subprocess('Agent did not terminate within '
                                   f'{SIGINT_TIMEOUT} seconds on SIGINT.')

        if self._timedout:
            stdout, stderr = self.proc.communicate(timeout=SIGINT_TIMEOUT)
            print(f'Here is stdout from {self.agent_name}:\n{stdout}')
            print(f'Here is stderr from {self.agent_name}:\n{stderr}')
            raise RuntimeError('Agent timed out.')


def create_agent_runner_fixture(agent_path, agent_name, args=None, timeout=60):
    """Create a pytest fixture for running a given OCS Agent.

    Parameters:
        agent_path (str): Relative path to Agent,
            i.e. '../agents/fake_data/fake_data_agent.py'
        agent_name (str): Short, unique name for the agent
        args (list): Additional CLI arguments to add when starting the Agent
        timeout (float): Timeout in seconds, after which the agent process will
            be interrupted. This typically indicates a crash within the agent.
            This timeout should be longer than you expect the agent to run for
            during a given test. Defaults to 60 seconds.

    """
    @pytest.fixture()
    def run_agent(cov):
        runner = _AgentRunner(agent_path, agent_name, args)
        runner.run(timeout=timeout)

        yield

        runner.shutdown()

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
                return client
            except RuntimeError as e:
                print(f"Caught error: {e}")
                print("Attempting to reconnect.")

            time.sleep(1)
            attempts += 1

        raise RuntimeError(
            f"Failed to connect to {instance_id} after {timeout} attempts.")

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
        <https://crossbar.io/docs/Node-Info-Service/>`_ running at the path
        /info.

    """
    attempts = 0

    while attempts < max_attempts:
        try:
            url = f"http://localhost:{port}/info"
            code = urllib.request.urlopen(url).getcode()
        except (URLError, ConnectionResetError):
            print("Crossbar server not online yet, waiting 5 seconds.")
            time.sleep(interval)

        attempts += 1

    assert code == 200
    print("Crossbar server online.")
