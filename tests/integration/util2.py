import os
import time
import pytest
import signal
import subprocess
import coverage.data


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

        # wait for Agent to connect
        time.sleep(1)

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
