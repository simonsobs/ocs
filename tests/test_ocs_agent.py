from ocs.ocs_agent import OCSAgent

from unittest.mock import MagicMock

import pytest
import pytest_twisted

from pathlib import Path

def tfunc(session, a):
    print(a)
    Path('./test.txt').touch()
    return True, 'words'
    
@pytest_twisted.inlineCallbacks
def test_agent():
    # Could be a test fixture to setup agent
    mock_config = MagicMock()
    mock_site_args = MagicMock()
    mock_site_args.log_dir = "./"
    a = OCSAgent(mock_config, mock_site_args, address='test.address')

    # insert a task into the Agent
    # TODO make 'test' an AgentTask (or maybe just call a.register_task()?
    #a.tasks = {'test_task': 'test'}
    a.register_task('test_task', tfunc)
    #a.agent_address = 'test.address'
    a.start('test_task')
    assert a.next_session_id == 1
    print(a.sessions['test_task'].encoded())
    # This is the deferred we get from threads.deferToThread -- we don't
    # actually wait for a respons here in this test...
    # TODO: do we want to do that? how would we do that?
    print(a.sessions['test_task'].d)
    #res = yield a.sessions['test_task'].d
    #print('result:', res)
    print(a.wait('test_task'))
    res = yield a.wait('test_task')
    print('result:', res)
