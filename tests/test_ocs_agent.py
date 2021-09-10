from ocs.ocs_agent import OCSAgent, AgentTask, AgentProcess

from unittest.mock import MagicMock

import pytest
import pytest_twisted


def tfunc(session, a):
    """Test function to call as a mocked OCS Task. We double it as the start
    and stop methods for test Processes too.

    """
    # These were useful in debugging twisted interactions
    # They're annoying when actually running tests though, as pytest can't
    # suppress the prints
    # print(a)
    # print("print from tfunc")
    return True, 'Task completed successfully'


def tfunc_raise(session, a):
    """Test Task that tries to raise an exception."""
    raise Exception('Look! An error!')
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


# Registration
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


# Start
def test_start_task(mock_agent):
    """Test a typical task that is blocking and already not running."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.start('test_task', params={'a': 1})
    # The Deferred we get from launching
    # mock_agent.sessions['test_task'].d
    print(res)
    assert res[0] == 0
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)


def test_start_unregistered_task(mock_agent):
    """Test a task that's not registered."""
    res = mock_agent.start('test_task', params={'a': 1})
    print(res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


# Wait
@pytest_twisted.inlineCallbacks
def test_wait(mock_agent):
    """Test an OCSAgent.wait() call on a short task that completes."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == 0
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)
    assert res[2] == {}


@pytest_twisted.inlineCallbacks
def test_wait_idle(mock_agent):
    """Test an OCSAgent.wait() call on an idle task with no session."""
    mock_agent.register_task('test_task', tfunc)
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == 0
    assert isinstance(res[1], str)
    assert res[2] == {}


@pytest_twisted.inlineCallbacks
def test_wait_expired_timeout(mock_agent):
    """Test an OCSAgent.wait() call with an already expired timeout."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task', timeout=-1)
    print('result:', res)
    assert res[0] == 1
    assert isinstance(res[1], str)
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
    assert isinstance(res[1], str)
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
    # Hmm, I thought maybe this would hit the except FirstErorr as e line, but
    # it doesn't.


# Stop
def test_stop_task(mock_agent):
    """Tasks don't support stop, we should get an error if we try to stop a
    Task.

    """
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.stop('test_task')
    print('result:', res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_stop_unregistered_process(mock_agent):
    """Trying to stop an unregistered process to return an error."""
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_stop_process(mock_agent):
    """Testing stop process with expected behavior."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.start('test_process', params={'a': 1})
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == 0
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_process'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}


def test_stop_process_no_session(mock_agent):
    """Stopping a process with no active session should return an error."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


# Abort
def test_abort(mock_agent):
    """Test an OCSAgent.abort() call."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.abort('test_task')
    print('result:', res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


# Status
def test_status(mock_agent):
    """Normally status will return OK, a message about the session, and the
    encoded session object.

    """
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = mock_agent.status('test_task')
    print('result:', res)
    assert res[0] == 0
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == 2
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}


def test_status_unregistered_task(mock_agent):
    """Requesting the status of an unregistered task should return an error."""
    res = mock_agent.status('test_task')
    print('result:', res)
    assert res[0] == -1
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_status_no_session(mock_agent):
    """Requesting the status of a task/process without a session returns OK,
    but with an informative message.

    """
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.status('test_task')
    print('result:', res)
    assert res[0] == 0
    assert isinstance(res[1], str)
    assert res[2] == {}
