from ocs.ocs_agent import OCSAgent, AgentTask, AgentProcess

from unittest.mock import MagicMock

import pytest
import pytest_twisted

from pathlib import Path

def tfunc(session, a):
    """Test function to call as a mocked OCS Task.

    This currently makes a file, as I wanted to see some external effect easily
    to know if the function ran while figuring out the twisted interaction.

    """
    print(a)
    Path('./test.txt').touch()
    return True, 'words'

@pytest.fixture
def mock_agent():
    """Test fixture to setup a mocked OCSAgent.

    """
    mock_config = MagicMock()
    mock_site_args = MagicMock()
    mock_site_args.log_dir = "./"
    a = OCSAgent(mock_config, mock_site_args, address='test.address')
    return a

def test_register_task(mock_agent):
    """Registered tasks should show up in the Agent tasks and sessions
    dicts.

    """
    mock_agent.register_task('test_task', tfunc)

    assert 'test_task' in mock_agent.tasks
    assert isinstance(mock_agent.tasks['test_task'], AgentTask)

    assert 'test_task' in mock_agent.sessions
    assert mock_agent.sessions['test_task'] is None

def test_register_task_w_startup(mock_agent):
    """Registering a task that should run on startup should place the task in
    the Agents startup_ops list.

    """
    mock_agent.register_task('test_task', tfunc, startup=True)

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == [('task', 'test_task', True)]

def test_register_process(mock_agent):
    """Registered processes should show up in the Agent processes and sessions
    dicts.

    """
    mock_agent.register_process('test_process', tfunc, tfunc)

    assert 'test_process' in mock_agent.processes
    assert isinstance(mock_agent.processes['test_process'], AgentProcess)

    assert 'test_process' in mock_agent.sessions
    assert mock_agent.sessions['test_process'] is None

def test_register_process_w_startup(mock_agent):
    """Registering a task that should run on startup should place the task in
    the Agents startup_ops list.

    """
    mock_agent.register_process('test_process', tfunc, tfunc, startup=True)

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == [('process', 'test_process', True)]

def test_agent_start(mock_agent):
    # insert a task into the Agent
    # TODO make 'test' an AgentTask (or maybe just call a.register_task()?
    #a.tasks = {'test_task': 'test'}
    mock_agent.register_task('test_task', tfunc)
    #a.agent_address = 'test.address'
    qq = mock_agent.start('test_task')
    assert mock_agent.next_session_id == 1
    print(mock_agent.sessions['test_task'].encoded())
    print(mock_agent.sessions['test_task'].d)
    print('look', qq)
    #print('result:', res)

@pytest_twisted.inlineCallbacks
def test_agent_wait(mock_agent):
    # insert a task into the Agent
    # TODO make 'test' an AgentTask (or maybe just call a.register_task()?
    #a.tasks = {'test_task': 'test'}
    mock_agent.register_task('test_task', tfunc)
    #a.agent_address = 'test.address'
    mock_agent.start('test_task')
    assert mock_agent.next_session_id == 1
    print(mock_agent.sessions['test_task'].encoded())
    # This is the deferred we get from threads.deferToThread -- we don't
    # actually wait for a respons here in this test...
    # TODO: do we want to do that? how would we do that?
    print(mock_agent.sessions['test_task'].d)
    #res = yield a.sessions['test_task'].d
    #print('result:', res)
    print(mock_agent.wait('test_task'))
    res = yield mock_agent.wait('test_task')
    print('result:', res)
