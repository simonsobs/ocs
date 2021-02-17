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
        params = {'procedure': control_client.agent_addr,
                  'args': ['get_tasks'], 'kwargs': {}}

        responses.add(responses.POST,
                      url='http://example.com/call',
                      #url='http://127.0.0.1:8001/call',
                      body='',
                      match=[
                        #responses.json_params_matcher({"procedure": "observatory.test", "args": ["get_tasks"], "kwargs": {}})
                        responses.json_params_matcher(params)
                      ],
                      json={"args": [[["delay_task", {"op_name": "delay_task", "status": "no_history"},
                                                     {"blocking": False,
                                                     "docstring": "Task docstring"}],
                                      ["set_heartbeat", {"op_name": "set_heartbeat", "status": "no_history"},
                                      {"blocking": True, "docstring": "Task to set the state of the agent heartbeat."}]]]}
                      
        )
        resp = control_client.get_tasks()
        #params = json.dumps({"args": 'get_tasks'})
                           
        #resp = requests.post('http://example.com/call', data=params, headers={'content-type': 'application/json'})
        #resp = requests.post('http://example.com/call', data=params)
        print(resp)
        #print(resp.json())

    @responses.activate
    def test_get_processes(self, control_client):
        """Start just passes"""
        params = {'procedure': control_client.agent_addr,
                  'args': ['get_processes'], 'kwargs': {}}
        ex_response = {"args": [[["acq",
                                  {"session_id": 0,
                                  "op_name": "acq",
                                  "status": "running",
                                  "start_time": 1613602407.7834675,
                                  "end_time": None,
                                  "success": None,
                                  "data": {"fields": {"channel_00": 0.09792315743251072,
                                                      "channel_01": 0.10505459024661522,
                                                      "channel_02": 0.09813845706627806,
                                                      "channel_03": 0.11473606863867097},
                                           "timestamp": 1613602476.5843427},
                                           "messages": [[1613602407.7834675, "Status is now \"starting\"."],
                                                        [1613602407.784276,"Status is now \"running\"."]]},
                                  {"blocking": True, "docstring":"Process docstring."}]]]}

        responses.add(responses.POST,
                      url='http://example.com/call',
                      #url='http://127.0.0.1:8001/call',
                      body='',
                      match=[
                        responses.json_params_matcher(params)
                      ],
                      json=ex_response
        )

        resp = control_client.get_processes()

        # Check some simple parts of the response
        assert resp[0][0] == 'acq'
        assert resp[0][1]['op_name'] == 'acq'
        assert resp[0][2]['blocking'] == True
