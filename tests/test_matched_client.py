import os
import pytest

from unittest.mock import MagicMock, patch

import ocs

from ocs.matched_client import (
    _humanized_time,
    _get_op,
    _opname_to_attr,
    MatchedClient,
)

from agents.util import create_session

mocked_client = MagicMock()
mock_from_yaml = MagicMock()


@patch('ocs.client_http.ControlClient', mocked_client)
@patch('ocs.site_config.SiteConfig.from_yaml', mock_from_yaml)
@patch('sys.argv', ['example_client.py', 'test'])
def test_extra_argv():
    """If there are extra arguments in sys.argv and args=[] is not set when
    instantiating a MatchedClient, then internally
    site_config.get_control_client() will inspect sys.argv[1:], which causes
    issues down the line when run through the site_config parser.

    Here we patch in a mocked ControlClient to avoid needing to talk to a
    crossbar server. We also patch in a mocked from_yaml() method, to avoid
    needing to read a real site file. Lastly, and most importantly, we patch in
    sys.argv with an actual additional argument. This will cause an
    "unrecognized arguments" error when argparse inspects sys.argv within the
    site_config parser.

    """
    # Set for get_config to pick up on
    os.environ["OCS_CONFIG_DIR"] = '/tmp/'
    MatchedClient("test")


@pytest.mark.parametrize('input_, expected',
                         [(0.1, '0.100000 s'),
                          (2, '2.0 s'),
                          (120*60-1, '120.0 mins'),
                          (48*3600-1, '48.0 hrs'),
                          (48*3600+1, '2.0 days'),
                          ])
def test_humanized_time(input_, expected):
    assert _humanized_time(input_) == expected


@pytest.mark.parametrize('input_, expected',
                         [('test_name', 'test_name'),
                          ('test-name', 'test_name'),
                          ('test name', 'test_name'),
                          ])
def test_opname_to_attr(input_, expected):
    assert _opname_to_attr(input_) == expected


def mock_client(session_name, response_code):
    """Mock a ControlClient object that has a predefined request response for
    an OpSession with the given name.

    Parameters:
        session_name (str): Name to give to the OpSession being called by
            ControlClient.request.
        response_code (int): Value of ResponseCode for the client.request call
            to return.

    """
    session = create_session(session_name)
    encoded_session = session.encoded()

    client = MagicMock()
    client.request = MagicMock(return_value=(response_code,
                                             'msg',
                                             encoded_session))

    return client


class TestGetOp:
    def test_invalid_op_type(self):
        with pytest.raises(ValueError):
            _get_op('not_valid', 'name', MagicMock(), MagicMock(), MagicMock())

    def _client_operation(self, op_type, op_name, response_code=ocs.OK):
        """Build a mocked client, and get an Operation for it, returning
        both.

        """
        client = mock_client(op_name, response_code)
        encoded_task = \
            MagicMock(return_value={'blocking': True,
                                    'docstring': 'Example docstring'})
        task = _get_op(op_type, op_name, None, encoded_task, client)

        return (client, task)

    @pytest.fixture
    def client_task(self):
        return self._client_operation('task', 'task_name')

    @pytest.fixture
    def client_process(self):
        return self._client_operation('process', 'process_name')

    def test_task_abort(self, client_task):
        client, task = client_task
        print(task.abort())
        client.request.assert_called_with('abort', 'task_name')

    def test_task_start(self, client_task):
        client, task = client_task
        print(task.start())
        client.request.assert_called_with('start', 'task_name', params={})

    def test_task_wait(self, client_task):
        client, task = client_task
        print(task.wait())
        client.request.assert_called_with('wait', 'task_name', timeout=None)

    def test_task_status(self, client_task):
        client, task = client_task
        print(task.status())
        client.request.assert_called_with('status', 'task_name')

    def test_task_call(self):
        client, task = self._client_operation('task', 'task_name', ocs.OK)
        print(task())
        # equivalent to 'start' + 'wait', but we can only check the last call
        client.request.assert_called_with('wait', 'task_name', timeout=None)

    def test_task_call_w_error(self):
        client, task = self._client_operation('task', 'task_name', ocs.ERROR)
        print(task())
        # error skips the 'wait' call after 'start'
        client.request.assert_called_with('start', 'task_name', params={})

    def test_process_stop(self, client_process):
        client, process = client_process
        print(process.stop())
        client.request.assert_called_with('stop', 'process_name')

    def test_process_call(self, client_process):
        client, process = client_process
        print(process())
        client.request.assert_called_with('status', 'process_name')
