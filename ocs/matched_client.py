from ocs import site_config


def get_op(op_type, name, session, encoded, client):
    """
    Factory for generating matched operations.
    This will make sure op.start's docstring is the docstring of the operation.
    """

    class MatchedOp:
        def start(self, **kwargs):
            return client.request('start', name, params=kwargs)

        def wait(self):
            return client.request('wait', name)

        def status(self):
            return client.request('status', name)

    class MatchedTask(MatchedOp):
        def abort(self):
            return client.request('abort', name)

    class MatchedProcess(MatchedOp):
        def stop(self):
            return client.request('stop', name)

    MatchedOp.start.__doc__ = encoded['docstring']

    if op_type == 'task':
        return MatchedTask()
    elif op_type == 'process':
        return MatchedProcess()
    else:
        raise ValueError("op_type must be either 'task' or 'process'")


def opname_to_attr(name):
    for c in ['-', ' ']:
        name = name.replace(c, '_')
    return name


class MatchedClient:
    """A convenient form of an OCS client, facilitating task/process calls.

    A MatchedClient is a general OCS Client that 'matches' an agent's
    tasks/processes to class attributes, making it easy to setup a client
    and call associated tasks and processes.

    Example:
        This example sets up a MatchedClient and calls a 'matched' task
        (init_lakeshore) and process (acq)::

            >>> client = MatchedClient('thermo1', client_type='http',
            ...                        args=[])
            >>> client.init_lakeshore.start()
            >>> client.init_lakeshore.wait()
            >>> client.acq.start(sampling_frequency=2.5)

    Attributes:
        instance_id (str): Instance id for agent to run

    """

    def __init__(self, instance_id, **kwargs):
        """MatchedClient __init__ function.

        Args:
            instance_id (str): Instance id for agent to run
            args (list or args object, optional):
                Takes in the parser arguments for the client.
                If None, reads from command line.
                If list, reads in list elements as arguments.
                Defaults to None.

        For additional kwargs see site_config.get_control_client.

        """
        self._client = site_config.get_control_client(instance_id, **kwargs)
        self.instance_id = instance_id

        for name, session, encoded in self._client.get_tasks():
            setattr(self, opname_to_attr(name),
                    get_op('task', name, session, encoded, self._client))

        for name, session, encoded in self._client.get_processes():
            setattr(self, opname_to_attr(name),
                    get_op('process', name, session, encoded, self._client))
