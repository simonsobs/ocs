from unittest.mock import MagicMock

import json
import pytest
import responses
import requests
from ocs.client_http import ControlClient


@pytest.fixture
def control_client():
    """Initialize ControlClient object."""
    master_addr = '%s.%s' % ('observatory', 'test')
    client = ControlClient(master_addr, url='http://example.com/call', realm='test_realm')
    #client = ControlClient(master_addr, url='http://127.0.0.1:8001/call', realm='test_realm')
    return client


class TestControlClient:
    """Test client_http.ControlClient class."""
    def test_control_client_creation(self, control_client):
        """Test we can create a ControlClient and attributes exist."""
        assert control_client.agent_addr == 'observatory.test'
        assert control_client.realm == 'test_realm'
        #assert control_client.call_url == 'http://127.0.0.1:8001/call'
        assert control_client.call_url == 'http://example.com/call'

    def test_start(self, control_client):
        """Start just passes"""
        assert control_client.start() is None

    def test_stop(self, control_client):
        """Start just passes"""
        assert control_client.stop() is None

    @responses.activate
    def test_get_tasks(self, control_client):
        """Start just passes"""
        responses.add(responses.POST,
                      url='http://example.com/call',
                      #body='',
                      #status=201,
                      match=[
                        #responses.json_params_matcher({"args": 'get_tasks'})
                        responses.json_params_matcher({"procedure": "observatory.test", "args": ["get_tasks"], "kwargs": {}})
                      ],
                      json={"args": [[["delay_task", {"op_name": "delay_task", "status": "no_history"},
                                                     {"blocking": False,
                                                     "docstring": "Task docstring"}],
                                      ["set_heartbeat", {"op_name": "set_heartbeat", "status": "no_history"},
                                      {"blocking": True, "docstring": "Task to set the state of the agent heartbeat."}]]]}
                      
        )
        #params = json.dumps({'procedure': control_client.agent_addr,
        #                     'args': ['get_tasks'], 'kwargs': []})
        #responses.add(responses.POST,
        #              url='http://example.com/call',
        #              #body='',
        #              status=201,
        #              match=[
        #                #responses.json_params_matcher({"args": 'get_tasks'})
        #                responses.json_params_matcher(params)
        #              ],
        #              json={'error': 'not found'}
        #              
        #)


        resp = control_client.get_tasks()
        #params = json.dumps({"args": 'get_tasks'})
                           
        #resp = requests.post('http://example.com/call', data=params, headers={'content-type': 'application/json'})
        #resp = requests.post('http://example.com/call', data=params)
        print(resp)
        print(dir(resp))
        #print(resp.json())



def example():
    """'wampy' client type should raise error."""
    master_addr = '%s.%s' % ('observatory', 'test')
    client = ControlClient(master_addr, url='http://127.0.0.1:8001', realm='test_realm')
    return client
