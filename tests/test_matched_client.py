from unittest.mock import patch

from ocs.matched_client import MatchedClient

from util import fake_get_control_client


class TestMatchedClient:
    @patch('ocs.site_config.get_control_client', fake_get_control_client)
    def test_matched_client_object(self):
        client = MatchedClient('agent-id')
        assert client.instance_id == 'agent-id'
        print(dir(client))
        assert hasattr(client, 'process_name')
        assert hasattr(client, 'task_name')
