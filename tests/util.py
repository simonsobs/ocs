from unittest.mock import MagicMock
import os

def fake_get_control_client(instance_id, **kwargs):
    """Quick function to return a Client like you'd expect from
    site_config.get_control_client, except it's mocked to have simple get_tasks
    and get_processes fixed values.

    """
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

    client.get_tasks = MagicMock(return_value=api['tasks'])
    client.get_processes = MagicMock(return_value=api['processes'])
    client.get_api = MagicMock(return_value=api)

    return client
