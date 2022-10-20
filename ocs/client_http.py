# The crossbar router must be configured to expose http access.
import json
import requests


class ControlClientError(RuntimeError):
    pass


class ControlClient():
    def __init__(self, agent_addr, **kwargs):
        self.agent_addr = agent_addr
        self.realm = kwargs['realm']
        self.call_url = kwargs['url']

    # start and stop are just to imitate wampy client...
    def start(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass

    def call(self, procedure, *args, **kwargs):
        # curl -H "Content-Type: application/json"
        #     -d '{"procedure": "observatory.acu1",
        #          "args": ["get_tasks"]}'
        #     http://127.0.0.1:8001/call
        params = json.dumps({'procedure': procedure,
                             'args': args, 'kwargs': kwargs})
        try:
            r = requests.post(self.call_url, data=params)
        except requests.exceptions.ConnectionError:
            raise ControlClientError([0, 0, 0, 0, 'client_http.error.connection_error',
                                      ['Failed to connect to %s' % self.call_url], {}])
        if r.status_code != 200:
            raise ControlClientError([0, 0, 0, 0, 'client_http.error.request_error',
                                      ['Server replied with code %i' % r.status_code], {}])
        decoded = r.json()
        if 'error' in decoded:
            # Return errors in the same way wampy does, roughly.
            raise ControlClientError([0, 0, 0, 0, decoded['error'], decoded['args'], decoded['kwargs']])
        return decoded['args'][0]

    def get_api(self, simple=False):
        """Query the API and other info from the Agent; this includes lists of
        Processes, Tasks, and Feeds, docstrings, operation session
        structures, and info about the Agent instance (class, PID,
        host).

        Args:
          simple (bool): If True, then return just the lists of the op
            and feed names without accompanying detail.

        Returns:
          A dict, see :func:`ocs.ocs_agent.OCSAgent._management_handler`
          for detail.

        """
        data = self.call(self.agent_addr, 'get_api')
        if not simple:
            return data
        return {k: [_v[0] for _v in v]
                for k, v in data.items() if isinstance(v, dict)}

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
