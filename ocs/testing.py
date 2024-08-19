import os
import time
import pytest
import signal
import subprocess
import coverage.data
import urllib.request

from threading import Thread, Timer
from urllib.error import URLError

from ocs.ocs_client import OCSClient

# Agent is run as subprocess
# Fixture checks that agent starts up properly after 1 second, raises an error with stdout/stderr printed if it doesn't
# agent is sent a SIGINT at end of tests (after `yield`
# fixture blocks (with `communicate()` for 10 seconds waiting for shutdown -- raises error with stdout/stderr printout if it fails to exit
# coverage is reported


SIGINT_TIMEOUT = 10


class AgentRunner:
    def __init__(self, agent_path, agent_name, args):
        self.env = os.environ.copy()
        self.env['COVERAGE_FILE'] = f'.coverage.agent.{agent_name}'
        self.env['OCS_CONFIG_DIR'] = os.getcwd()
        # running unbuffered (-u) is important for getting agent stdout/stderr
        self.cmd = ['python',
                    '-u',
                    '-m',
                    'coverage',
                    'run',
                    '--rcfile=./.coveragerc',
                    agent_path,
                    '--site-file',
                    './default.yaml']
        if args is not None:
            self.cmd.extend(args)

        self.proc = None
        self.timers = {'run': None,
                       'interrupt': None}
        self.agent_name = agent_name
        self._comm_thread = None

    def _communicate(self):
        # this actually needs to happen in another thread, since it's going to
        # block and we need to yield after this
        try:
            # TODO: We should grab stdout/stderr from here instead of from self.proc.stdout.read()
            self.proc.communicate()
        finally:
            self._cleanup()

    def run(self, timeout):
        self.proc = subprocess.Popen(self.cmd,
                                     env=self.env,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     preexec_fn=os.setsid)
        self.timers['run'] = Timer(timeout, self.interrupt)
        self.timers['run'].start()

        # Wait briefly then make sure subprocess hasn't already exited.
        time.sleep(1)
        if self.proc.poll() is not None:
            self._raise_subprocess(f"Agent failed to startup, cmd: {self.cmd}")

        self._comm_thread = Thread(target=self._communicate)
        self._comm_thread.start()

    def shutdown(self):
        # shutdown Agent
        self.interrupt()

        _error = f'Agent did not terminate within {SIGINT_TIMEOUT} seconds on SIGINT.'
        interrupt_timer = Timer(SIGINT_TIMEOUT, self.interrupt, kwargs={'msg': _error})
        interrupt_timer.start()

        # wrap up comm thread
        self._comm_thread.join()
        interrupt_timer.cancel()

    def interrupt(self, msg=None):
        self.proc.send_signal(signal.SIGINT)
        self._read_output()
        self._raise_subprocess(msg)

    def _send_sigint(self):
        self.proc.send_signal(signal.SIGINT)

    def _read_output(self):
        stdout, stderr = self.proc.stdout.read(), self.proc.stderr.read()
        print(f'Here is stdout from {self.agent_name}:\n{stdout}')
        print(f'Here is stderr from {self.agent_name}:\n{stderr}')
        return stdout, stderr

    def _cleanup(self):
        # Cancel all timers
        for timer in self.timers.values():
            if timer is not None:
                timer.cancel()

    def _raise_subprocess(self, msg):
        self._cleanup()
        raise RuntimeError(msg)


def create_agent_runner_fixture(agent_path, agent_name, args=None, timeout=60):
    """Create a pytest fixture for running a given OCS Agent.

    Parameters:
        agent_path (str): Relative path to Agent,
            i.e. '../agents/fake_data/fake_data_agent.py'
        agent_name (str): Short, unique name for the agent
        args (list): Additional CLI arguments to add when starting the Agent
        timeout (float): Timeout in seconds, after which the agent process will
            be killed. This typically indicates a crash within the agent.
            Defaults to 60 seconds.

    """
    @pytest.fixture()
    def run_agent(cov):
        runner = AgentRunner(agent_path, agent_name, args)
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
