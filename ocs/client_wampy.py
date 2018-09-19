# The wampy library provides synchronous (blocking) access to a WAMP
# router.  However, the default implementation assumes a very
# particular format for the data returned by a remote function (see
# wampy/messages/result.py:Result.value, which returns
# kwargs['message']), so we subclass the usual client and provide our
# own call function, which returns the first element of arglist (see
# WAMP "RESULT" specification).

from wampy.peers import Client as WampyClient
from wampy.messages.call import Call as WampyCall

class ControlClient(WampyClient):
    def __init__(self, agent_addr, **kwargs):
        WampyClient.__init__(self, **kwargs)
        self.agent_addr = agent_addr
        
    # This override is important.
    def call(self, procedure, *args, **kwargs):
        message = WampyCall(procedure=procedure, args=args, kwargs=kwargs)
        response = self.make_rpc(message)
        if not hasattr(response, 'yield_args'):
            raise RuntimeError(response.message)
        return response.yield_args[0]

    def get_tasks(self):
        return self.call(self.agent_addr + '.get_tasks')
    
    def get_processes(self):
        return self.call(self.agent_addr + '.get_processes')
    
    def request(self, action, op_name, args):
        return self.call(self.agent_addr + '.ops', action, op_name)
    
