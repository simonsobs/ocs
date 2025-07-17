import collections
import time

import ocs
from ocs import site_config, access

import logging
logger = logging.getLogger(__name__)


def _get_op(op_type, name, encoded, client, password):
    """Factory for generating matched operations. This will make sure
    op.start's docstring is the docstring of the operation.

    Parameters:
        op_type (str): Operation type, either 'task' or 'process'.
        name (str): Operation name
        encoded (dict): Encoded :class:`ocs.ocs_agent.AgentTask` or
            :class:`ocs.ocs_agent.AgentProcess` dictionary.
        client (ControlClient): Client object, which will be used to issue the
            requests for operation actions.
        password (str): Client-supplied password, or None to not use a
            password.

    """
    # It's important to not pass password='', if the agent doesn't
    # support password API.
    feature_kw = {}
    if password is not None and password != '':
        feature_kw['password'] = password

    class MatchedOp:
        def start(self, **kwargs):
            return OCSReply(*client.request('start', name, params=kwargs,
                                            **feature_kw))

        def wait(self, timeout=None):
            return OCSReply(*client.request('wait', name, timeout=timeout,
                                            **feature_kw))

        def status(self):
            return OCSReply(*client.request('status', name,
                                            **feature_kw))

    class MatchedTask(MatchedOp):
        def abort(self):
            return OCSReply(*client.request('abort', name,
                                            **feature_kw))

        def __call__(self, **kw):
            """Runs self.start(**kw) and, if that succeeds, self.wait()."""
            result = self.start(**kw)
            if result[0] != ocs.OK:
                return result
            return self.wait()

    class MatchedProcess(MatchedOp):
        def stop(self):
            return OCSReply(*client.request('stop', name,
                                            **feature_kw))

        def __call__(self):
            """Equivalent to self.status()."""
            return self.status()

    MatchedOp.start.__doc__ = encoded['docstring']

    if op_type == 'task':
        return MatchedTask()
    elif op_type == 'process':
        return MatchedProcess()
    else:
        raise ValueError("op_type must be either 'task' or 'process'")


def _opname_to_attr(name):
    for c in ['-', ' ']:
        name = name.replace(c, '_')
    return name


class OCSClient:
    """The simple OCS Client, facilitating task/process calls.

    OCSClient makes an Agent's tasks/processes available as class attributes,
    making it easy to setup a client instance and call the associated Agent's
    tasks and processes.

    Example:
        This example sets up an OCSClient object and calls a FakeDataAgent's
        Task (delay_task) and process (acq)::

            >>> client = OCSClient('fake-data-1')
            >>> client.delay_task(delay=5)
            >>> client.acq.start()

    Attributes:
        instance_id (str): instance-id for agent to run

    """

    def __init__(self, instance_id, privs=None, **kwargs):
        """
        Args:
            instance_id (str): Instance id for agent to run
            args (list or args object, optional):
                Takes in the parser arguments for the client.
                If None, pass an empty list.
                If list, reads in list elements as arguments.
                Defaults to None.

        .. note::
            For additional ``**kwargs`` see site_config.get_control_client.

        """
        if kwargs.get('args') is None:
            kwargs['args'] = []

        self._client = site_config.get_control_client(instance_id, **kwargs)
        self.instance_id = instance_id
        self._api = self._client.get_api()

        # If target agent doesn't support AC, don't pass password arg.
        use_password = (self._api.get('access_control') is not None)

        self._password = access.client_get_password(
            privs, self._api['agent_class'], instance_id)

        if self._password not in [None, ''] and not use_password:
            logger.warning('WARNING: client wants to pass a password to '
                           'agent instance, but it does not support passwords.')
            self._password = None

        for name, _, encoded in self._api['tasks']:
            setattr(self, _opname_to_attr(name),
                    _get_op('task', name, encoded, self._client, self._password))

        for name, _, encoded in self._api['processes']:
            setattr(self, _opname_to_attr(name),
                    _get_op('process', name, encoded, self._client, self._password))

    def __repr__(self):
        return f"OCSClient('{self.instance_id}')"


def _humanized_time(t):
    if abs(t) < 1.:
        return '%.6f s' % t
    if abs(t) < 120:
        return '%.1f s' % t
    if abs(t) < 120 * 60:
        return '%.1f mins' % (t / 60)
    if abs(t) < 48 * 3600:
        return '%.1f hrs' % (t / 3600)
    return '%.1f days' % (t / 86400)


class OCSReply(collections.namedtuple('_OCSReply',
                                      ['status', 'msg', 'session'])):
    def __repr__(self):
        try:
            ok_str = ocs.ResponseCode(self.status).name
        except ValueError:
            ok_str = '???'
        text = 'OCSReply: %s : %s\n' % (ok_str, self.msg)
        if self.session is None or len(self.session.keys()) == 0:
            return text + '  (no session -- op has never run)'

        # try/fail in here so we can make assumptions about key
        # presence and bail out to a full dump if anything is weird.
        try:
            handled = ['op_name', 'session_id', 'status', 'start_time',
                       'end_time', 'messages', 'success']

            s = self.session
            run_str = 'status={status}'.format(**s)
            if s['status'] in ['starting', 'running']:
                run_str += ' for %s' % _humanized_time(
                    time.time() - s['start_time'])
            elif s['status'] == 'done':
                if s['success']:
                    run_str += ' without error'
                else:
                    run_str += ' with ERROR'
                run_str += ' %s ago, took %s' % (
                    _humanized_time(time.time() - s['end_time']),
                    _humanized_time(s['end_time'] - s['start_time']))
            text += ('  {op_name}[session={session_id}]; '
                     '{run_str}\n'.format(run_str=run_str, **s))
            messages = s.get('messages', [])
            if len(messages):
                to_show = min(5, len(messages))
                text += ('  messages (%i of %i):\n' % (to_show, len(messages)))
                for m in messages:
                    text += '    %.3f %s\n' % (m[0], m[1])

            also = [k for k in s.keys() if k not in handled]
            if len(also):
                text += ('  other keys in .session: ' + ', '.join(also))

        except Exception as e:
            text += ('\n  [session decode failed with exception: %s\n'
                     '  Here is everything in .session:\n %s\n]') \
                % (e.args, self.session)
        return text
