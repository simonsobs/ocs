from unittest.mock import MagicMock


def fake_get_control_client(instance_id, **kwargs):
    """Quick function to return a Client like you'd expect from
    site_config.get_control_client, except it's mocked to have simple get_tasks
    and get_processes fixed values.

    """
    encoded_op = {'blocking': True,
                  'docstring': 'Example docstring'}
    client = MagicMock()
    client.get_tasks = MagicMock(return_value=([('task_name',
                                               None,
                                               encoded_op)]))
    client.get_processes = MagicMock(return_value=([('process_name',
                                                     None,
                                                     encoded_op)]))

    return client
