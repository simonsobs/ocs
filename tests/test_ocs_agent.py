from ocs.ocs_agent import OCSAgent, AgentTask, AgentProcess

from unittest.mock import MagicMock
from twisted.internet.defer import Deferred

import pytest
import pytest_twisted

from pathlib import Path

def tfunc(session, a):
    """Test function to call as a mocked OCS Task.

    This currently makes a file, as I wanted to see some external effect easily
    to know if the function ran while figuring out the twisted interaction.

    """
    print(a)
    print("print from tfunc")
    Path('./test.txt').touch()
    return True, 'words'

def tfunc_raise(session, a):
    """Test function to call as a mocked OCS Task.

    This currently makes a file, as I wanted to see some external effect easily
    to know if the function ran while figuring out the twisted interaction.

    """
    raise Exception('look an error')
    return tfunc(session, a)

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

def test_start_task(mock_agent):
    """Test a typical task that is blocking and already not running."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.start('test_task', params={'a': 1})
    # The Deferred we get from launching
    # mock_agent.sessions['test_task'].d
    print(res)
    assert res[0] == 0
    assert res[1] == 'Started task "test_task".'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}

def test_start_process(mock_agent):
    """Test a typical process that is blocking and already not running."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.start('test_process', params={'a': 1})
    print(res)
    assert res[0] == 0
    assert res[1] == 'Started process "test_process".'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_process'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}

def test_start_nonblocking_task(mock_agent):
    """Test a typical task that is non-blocking and already not running."""
    mock_agent.register_task('test_task', tfunc, blocking=False)
    res = mock_agent.start('test_task', params={'a': 1})
    # The Deferred we get from launching
    # mock_agent.sessions['test_task'].d
    print(res)
    assert res[0] == 0
    assert res[1] == 'Started task "test_task".'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}

def test_start_task_done_status(mock_agent):
    """Test a task that's already marked as 'done'. In this case, we expect
    output to match test_start(), so the same asserts are made.

    """
    mock_agent.register_task('test_task', tfunc)

    # set session to 'done'
    mock_session = MagicMock()
    mock_session.status = 'done'
    mock_agent.sessions['test_task'] = mock_session

    res = mock_agent.start('test_task', params={'a': 1})
    print(res)
    assert res[0] == 0
    assert res[1] == 'Started task "test_task".'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}

def test_start_task_other_status(mock_agent):
    """Test a task that's already marked as 'running'. In this case, we expect
    an error.

    Not sure we particularly care about the encoded session, so we just use a
    Mock session.

    """
    mock_agent.register_task('test_task', tfunc)

    # set session to 'running'
    mock_session = MagicMock()
    mock_session.status = 'running'
    mock_agent.sessions['test_task'] = mock_session

    res = mock_agent.start('test_task', params={'a': 1})
    print(res)
    assert res[0] == -1
    assert res[1] == 'Operation "test_task" already in progress.'

def test_start_unregistered_task(mock_agent):
    """Test a task that's not registered."""
    res = mock_agent.start('test_task', params={'a': 1})
    print(res)
    assert res[0] == -1
    assert res[1] == 'No task or process called "test_task"'
    assert res[2] == {}

@pytest_twisted.inlineCallbacks
def test_wait(mock_agent):
    """Test an OCSAgent.wait() call on a short task that completes."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == 0
    assert res[1] == 'Operation "test_task" is currently not running (SUCCEEDED).'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 5
    assert res[2]['status'] == 'done'
    assert res[2]['success'] is True
    assert res[2]['end_time'] > res[2]['start_time']
    assert res[2]['data'] == {}

@pytest_twisted.inlineCallbacks
def test_wait_unregistered_task(mock_agent):
    """Test an OCSAgent.wait() call on an unregistered task."""
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == -1
    assert res[1] == 'Unknown operation "test_task".'
    assert res[2] == {}

@pytest_twisted.inlineCallbacks
def test_wait_idle(mock_agent):
    """Test an OCSAgent.wait() call on an idle task with no session."""
    mock_agent.register_task('test_task', tfunc)
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == 0
    assert res[1] == 'Idle.'
    assert res[2] == {}

@pytest_twisted.inlineCallbacks
def test_wait_expired_timeout(mock_agent):
    """Test an OCSAgent.wait() call with an already expired timeout."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task', timeout=-1)
    print('result:', res)
    assert res[0] == 1
    assert res[1] == 'Operation "test_task" still running; wait timed out.'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}

@pytest_twisted.inlineCallbacks
def test_wait_timeout(mock_agent):
    """Test an OCSAgent.wait() call with a timeout."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task', timeout=1)
    print('result:', res)
    assert res[0] == 0
    assert res[1] == 'Operation "test_task" is currently not running (SUCCEEDED).'
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 5
    assert res[2]['status'] == 'done'
    assert res[2]['success'] is True
    assert res[2]['end_time'] > res[2]['start_time']
    assert res[2]['data'] == {}

@pytest_twisted.inlineCallbacks
def test_wait_timeout_w_error(mock_agent):
    """Test an OCSAgent.wait() call with a timeout where an error is raised."""
    mock_agent.register_task('test_task', tfunc_raise)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task', timeout=1)
    print('result:', res)
    # Hmm, I thought maybe this would hit the except FirstErorr as e line, but it doesn't.

def test_abort(mock_agent):
    """Test an OCSAgent.abort() call."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.abort('test_task')
    print('result:', res)
    assert res[0] == -1
    assert res[1] == 'No implementation of abort() for operation "test_task"'
    assert res[2] == {}
