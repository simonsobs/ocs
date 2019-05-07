from ocs import site_config


class MatchedOp:
    def __init__(self, name, session, encoded, client):
        self.name = name
        self.__doc__ = encoded['docstring']
        self.client = client

    def start(self, **kwargs):
        return self.client.request('start', self.name, params=kwargs)


class MatchedTask(MatchedOp):
    def wait(self):
        return self.client.request('wait', self.name)

    def abort(self):
        return self.client.request('abort', self.name)


class MatchedProcess(MatchedOp):
    def stop(self):
        return self.client.request('stop', self.name)


def opname_to_attr(name):
    for c in ['-', ' ']:
        name = name.replace(c, '_')
    return name


class MatchedClient:
    def __init__(self, instance_id, client_type='http', args=None):
        """
        A general Matched Client that sets an agent's tasks/processes as attributes.
        To run ::

            client = MatchedClient('thermo1', client_type='http', args=[])

            client.init_lakeshore.start()
            client.init_lakeshore.wait()

            client.acq.start(sampling_frequency=2.5)

        Args:

             instance_id (string): Instance id for agent to run
             client_type (string, opt): Either 'http' or 'wampy'. Defaults to 'http'.
             args (list or args object):
                    Takes in the parser arguments for the client.
                    If None, reads from command line.
                    If list, reads in list elements as arguments.
                    Defaults to None.
        """
        self.client = site_config.get_control_client(instance_id,
                                                     client_type=client_type,
                                                     args=args)
        for name, session, encoded in self.client.get_tasks():
            setattr(self, opname_to_attr(name),
                    MatchedTask(name, session, encoded, self.client))

        for name, session, encoded in self.client.get_processes():
            setattr(self, opname_to_attr(name),
                    MatchedProcess(name, session, encoded, self.client))