import ocs
from ocs.ocs_agent import (
    OCSAgent, AgentTask, AgentProcess,
    ParamError, ParamHandler, param,
    OpSession
)
from ocs.base import OpCode

from unittest.mock import MagicMock

import pytest
import pytest_twisted

import json
import math
import numpy as np


def create_session(op_name):
    """Create an OpSession with a mocked app for testing."""
    mock_app = MagicMock()
    session = OpSession(1, op_name, app=mock_app)

    return session


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


@param('test', default=1)
def tfunc_param_dec(session, a):
    """tfunc but decorated with @ocs_agent.param."""
    return True, 'Task completed successfully'


@pytest.fixture
def mock_agent():
    """Test fixture to setup a mocked OCSAgent.

    """
    mock_config = MagicMock()
    mock_site_args = MagicMock()
    mock_site_args.working_dir = "./"
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


def test_register_task_wo_startup(mock_agent):
    """Registering a task that should not run on startup should leave the
    startup_ops list empty.

    """
    mock_agent.register_task('test_task', tfunc, startup=False)

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == []


def test_register_task_w_startup_dict(mock_agent):
    """Registering a task that should run on startup and passing a dict to
    startup, should place the task in the Agent's startup_ops list with that
    dict.

    """
    mock_agent.register_task('test_task', tfunc, startup={'arg1': 12})

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == [('task', 'test_task', {'arg1': 12})]


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


def test_register_process_wo_startup(mock_agent):
    """Registering a task that should not run on startup should leave the
    the Agents startup_ops list empty.

    """
    mock_agent.register_process('test_process', tfunc, tfunc, startup=False)

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == []


def test_register_process_w_startup_dict(mock_agent):
    """Registering a process that should run on startup and passing a dict to
    startup, should place the process in the Agent's startup_ops list with that
    dict.

    """
    mock_agent.register_process('test_process', tfunc, tfunc, startup={'arg1': 12})

    print(mock_agent.startup_ops)
    assert mock_agent.startup_ops == [('process', 'test_process', {'arg1': 12})]


# Start
def test_start_task(mock_agent):
    """Test a typical task that is blocking and already not running."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.start('test_task', params={'a': 1})
    # The Deferred we get from launching
    # mock_agent.sessions['test_task'].d
    print(res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.STARTING.value
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}


def test_start_process(mock_agent):
    """Test a typical process that is blocking and already not running."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.start('test_process', params={'a': 1})
    print(res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_process'
    assert res[2]['op_code'] == OpCode.STARTING.value
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
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.STARTING.value
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
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.STARTING.value
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
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)


def test_start_unregistered_task(mock_agent):
    """Test a task that's not registered."""
    res = mock_agent.start('test_task', params={'a': 1})
    print(res)
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_start_task_none_params(mock_agent):
    """Test passing params=None to task decorated with @param that has set
    defaults.

    See issue: https://github.com/simonsobs/ocs/issues/251

    """
    mock_agent.register_task('test_task', tfunc_param_dec)
    res = mock_agent.start('test_task', params=None)
    print(res)
    assert res[0] == ocs.OK


# Wait
@pytest_twisted.inlineCallbacks
def test_wait(mock_agent):
    """Test an OCSAgent.wait() call on a short task that completes."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.SUCCEEDED.value
    assert res[2]['status'] == 'done'
    assert res[2]['success'] is True
    assert res[2]['end_time'] > res[2]['start_time']
    assert res[2]['data'] == {}


@pytest_twisted.inlineCallbacks
def test_wait_unregistered_task(mock_agent):
    """Test an OCSAgent.wait() call on an unregistered task."""
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


@pytest_twisted.inlineCallbacks
def test_wait_idle(mock_agent):
    """Test an OCSAgent.wait() call on an idle task with no session."""
    mock_agent.register_task('test_task', tfunc)
    res = yield mock_agent.wait('test_task')
    print('result:', res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2] == {}


@pytest_twisted.inlineCallbacks
def test_wait_expired_timeout(mock_agent):
    """Test an OCSAgent.wait() call with an already expired timeout."""
    mock_agent.register_task('test_task', tfunc)
    mock_agent.start('test_task')
    res = yield mock_agent.wait('test_task', timeout=-1)
    print('result:', res)
    assert res[0] == ocs.TIMEOUT
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.STARTING.value
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
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.SUCCEEDED.value
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
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_stop_unregistered_process(mock_agent):
    """Trying to stop an unregistered process to return an error."""
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_stop_process(mock_agent):
    """Testing stop process with expected behavior."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.start('test_process', params={'a': 1})
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_process'
    assert res[2]['op_code'] == OpCode.STARTING.value
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}


def test_stop_process_no_session(mock_agent):
    """Stopping a process with no active session should return an error."""
    mock_agent.register_process('test_process', tfunc, tfunc)
    res = mock_agent.stop('test_process')
    print('result:', res)
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


# Abort
def test_abort(mock_agent):
    """Test an OCSAgent.abort() call."""
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.abort('test_task')
    print('result:', res)
    assert res[0] == ocs.ERROR
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
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2]['session_id'] == 0
    assert res[2]['op_name'] == 'test_task'
    assert res[2]['op_code'] == OpCode.STARTING.value
    assert res[2]['status'] == 'starting'
    assert res[2]['success'] is None
    assert res[2]['end_time'] is None
    assert res[2]['data'] == {}


def test_status_unregistered_task(mock_agent):
    """Requesting the status of an unregistered task should return an error."""
    res = mock_agent.status('test_task')
    print('result:', res)
    assert res[0] == ocs.ERROR
    assert isinstance(res[1], str)
    assert res[2] == {}


def test_status_no_session(mock_agent):
    """Requesting the status of a task/process without a session returns OK,
    but with an informative message.

    """
    mock_agent.register_task('test_task', tfunc)
    res = mock_agent.status('test_task')
    print('result:', res)
    assert res[0] == ocs.OK
    assert isinstance(res[1], str)
    assert res[2] == {}


@pytest.mark.parametrize("key,value,expected", [('a', 1, 1),
                                                ('b', 'string', 'string'),
                                                ('c', [1, 2., 'blech'], [1, 2., 'blech']),
                                                ('d', [1., 2., math.nan], [1., 2., None]),
                                                ('e', np.int64(10), 10),
                                                ('f', np.array([10, 20, 30]), [10, 20, 30]),
                                                ('g', np.array([1., 2., math.nan]), [1., 2., None]),
                                                ('h', {'x': math.nan}, {'x': None})])
def test_session_data_good(key, value, expected):
    """Test that session.data is encoded as expected and can be
    JSON-serialized.

    """
    session = create_session('test_encoding')
    session.data = {key: value}

    encoded = session.encoded()
    print(encoded['data'])

    data = encoded['data']
    assert (key in data)
    assert data[key] == expected

    json.dumps(data, allow_nan=False)


@pytest.mark.parametrize("key,value", [('fail_a', math.inf),
                                       ('fail_b', [1., 2., -math.inf]),
                                       ('fail_c', {'x': math.inf})])
def test_session_data_bad(key, value):
    """Test that invalid session.data raises an error."""

    session = create_session('test_encoding')
    session.data = {key: value}

    with pytest.raises(ValueError):
        session.encoded()


#
# Tests for the @param decorator
#

def test_params_get():
    """Test that defaults & casting work as expected."""
    params = ParamHandler({
        'int_param': 123,
        'string_param': 'blech',
        'float_param': 1e8,
        'numerical_string_param': '145.12',
        'none_param': None,
    })

    # Basic successes
    params.get('int_param', type=int)
    params.get('string_param', type=str)
    params.get('float_param', type=float)

    # Tricky successes
    params.get('int_param', type=float)
    params.get('numerical_string_param', type=float, cast=float)

    # Defaults
    assert params.get('missing', default=10) == 10

    # None handling
    assert params.get('none_param', default=None) is None
    assert params.get('none_param', default=123) == 123
    with pytest.raises(ParamError):
        params.get('none_param')
    assert params.get('none_param', default=123,
                      treat_none_as_missing=False) is None

    # Basic failures
    with pytest.raises(ParamError):
        params.get('string_param', type=float)
    with pytest.raises(ParamError):
        params.get('float_param', type=str)
    with pytest.raises(ParamError):
        params.get('numerical_string_param', type=float)
    with pytest.raises(ParamError):
        params.get('string_param', type=float, cast=float)
    with pytest.raises(ParamError):
        params.get('missing')

    # Check functions
    params.get('int_param', check=lambda i: i > 0)
    with pytest.raises(ParamError):
        params.get('int_param', check=lambda i: i < 0)

    # Choices
    params.get('string_param', choices=['blech', 'a', 'b'])
    with pytest.raises(ParamError):
        params.get('string_param', choices=['a', 'b'])


def test_params_strays():
    """Test for detection of stray parameters."""
    params = ParamHandler({
        'a': 123,
        'b': 123,
    })
    params.get('a')
    params.check_for_strays(ignore=['b'])
    with pytest.raises(ParamError):
        params.check_for_strays()
    params.get('b')
    params.check_for_strays()


def test_params_decorator():
    """Test that the decorator is usable."""
    # this should work
    @param('a', default=12)
    def test_func(session, params):
        pass
    # these should not
    with pytest.raises(TypeError):
        @param('a', 12)
        def test_func2(session, params):
            pass
    with pytest.raises(TypeError):
        @param('a', invalid_keyword='something')
        def test_func3(session, params):
            pass


def test_params_decorated():
    """Test that the decorator actually decorates."""
    @param('a', default=12)
    def func_a(session, params):
        pass

    @param('_', default=12)
    def func_nothing(session, params):
        pass

    @param('a', default=12)
    @param('_no_check_strays')
    def func_whatever(session, params):
        pass

    ParamHandler({}).batch(func_a._ocs_prescreen)
    ParamHandler({'b': 12.}).batch(func_whatever._ocs_prescreen)

    with pytest.raises(ParamError):
        ParamHandler({'b': 12.}).batch(func_a._ocs_prescreen)
    with pytest.raises(ParamError):
        ParamHandler({'b': 12.}).batch(func_nothing._ocs_prescreen)
