from ocs import site_config


class MatchedOp:
    def __init__(self, name, session, client):
        self.name = name
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
        self.client = site_config.get_control_client(instance_id,
                                                     client_type=client_type,
                                                     args=args)

        for name, session in self.client.get_tasks():
            setattr(self, opname_to_attr(name),
                    MatchedTask(name, session, self.client))

        for name, session in self.client.get_processes():
            setattr(self, opname_to_attr(name),
                    MatchedProcess(name, session, self.client))