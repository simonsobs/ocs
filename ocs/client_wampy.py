# The wampy library provides synchronous (blocking) access to a WAMP
# router.  However, the default implementation assumes a very
# particular format for the data returned by a remote function (see
# wampy/messages/result.py:Result.value, which returns
# kwargs['message']), so we subclass the usual client and provide our
# own call function, which returns the first element of arglist (see
# WAMP "RESULT" specification).

try:
    # wampy (0.9.20) requires this gevent patch, but a warning is
    # issued because the patch occurs too late.  So this avoids the
    # warning, and maybe makes the patch work better?
    import gevent.monkey

    # Checks if patch_all has already been run.
    if '_gevent_saved_patch_all' not in gevent.monkey.saved:
        gevent.monkey.patch_all()

except ImportError:
    pass

from wampy.peers import Client as WampyClient
from wampy.messages.call import Call as WampyCall
from wampy.errors import WampyError

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

    def subscribe(self, topic, handler):
        """Assign a handler function to a pubsub topic.

        Discussion: the wampy documentation suggests using the
        decorator @subscribe to connect pubsub channels with handling
        functions.  The main problem with this is that channels can't
        be added dynamically, and a single function can be associated
        with multiple pubsub topics.
        """
        self.session._subscribe_to_topic(handler, topic)

    # These are API we want to add.

    def get_tasks(self):
        """
        Query the list of Tasks from the Agent management interface.

        Returns a list of items of the form (task_name, info_dict).
        """
        return self.call(self.agent_addr, 'get_tasks')

    def get_processes(self):
        """
        Query the list of Processes from the Agent management interface.

        Returns a list of items of the form (process_name, info_dict).
        """
        return self.call(self.agent_addr, 'get_processes')

    def get_feeds(self):
        """
        Query the list of Feeds from the Agent management interface.

        Returns a list of items of the form (feed_name, info_dict).
        """
        return self.call(self.agent_addr, 'get_feeds')


    def request(self, action, op_name, params={}, **kw):
        """
        Issue a request on an Agent's .ops interface.

        Args:
          action (string): The action name (start, status, etc).
          params (dict): Parameters to pass to the action.

        Returns:
          Tuple (status, message, session).
        """
        return self.call(self.agent_addr + '.ops', action, op_name, params, **kw)
