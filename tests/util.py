from unittest.mock import MagicMock
import os
import pytest
import yaml


def fake_get_control_client(has_access_control=True):
    """Quick function to return a Client like you'd expect from
    site_config.get_control_client, except it's mocked to have simple
    get_tasks and get_processes fixed values.

    """

    def _fake_get_control_client(instance_id, **kwargs):
        encoded_op = {'blocking': True,
                      'docstring': 'Example docstring'}
        client = MagicMock()  # mocks client_http.ControlClient

        # The api structure is defined by OCSAgent._management_handler
        api = {
            'tasks': [('task_name', None, encoded_op)],
            'processes': [('process_name', None, encoded_op)],
            'feeds': [],
            'agent_class': 'Mock',
            'instance_hostname': 'testhost',
            'instance_pid': os.getpid(),
        }
        if has_access_control:
            api['access_control'] = {
                'version': 1,
            }

        client.get_tasks = MagicMock(return_value=api['tasks'])
        client.get_processes = MagicMock(return_value=api['processes'])
        client.get_api = MagicMock(return_value=api)

        return client

    return _fake_get_control_client


@pytest.fixture(scope='session')
def password_file(tmp_path_factory):
    """Create a client password file at temporary location and return the path."""
    fn = tmp_path_factory.mktemp('ocs') / 'passwords.yaml'
    yaml.dump([
        {'default': True,
         'password_2': 'two'},
        {'instance_id': 'test-agent1',
         'password_2': 'ta-two',
         'password_3': 'ta-three'},
        {'agent_class': 'TestAgent',
         'password_2': 'TA-two'},
        {'agent_class': '!NormalAgent',
         'password_2': 'spec-test'},
    ], fn.open('w'))
    return fn
