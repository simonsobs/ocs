import ocs

import txaio
txaio.use_twisted()

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ReactorNotRunning

from autobahn.wamp.types import ComponentConfig
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.twisted.util import sleep as dsleep

def run_control_script(function, *args, **kwargs):
    cfg = ocs.get_ocs_config()
    server, realm = cfg.get('default', 'wamp_server'), cfg.get('default', 'wamp_realm')
    session = ControlClientSession(ComponentConfig(realm, {}), function, args, kwargs)
    runner = ApplicationRunner(server, realm)
    runner.run(session, auto_reconnect=True)

def run_control_script2(function, *args, **kwargs):
    """
    Run a function in a ControlClientSession.  The command line is
    parsed and site configuration information is loaded.  The function
    is invoked as

        function(root_address, *args, **kwargs)

    where root_address has been figured out based on system configuration.
    """
    parser = ocs.site_config.add_arguments()
    pargs = parser.parse_args()
    ocs.site_config.reparse_args(pargs, '*control*')
    server, realm = pargs.site_hub, pargs.site_realm
    addr = pargs.address_root
    session = ControlClientSession(ComponentConfig(realm, {}), function,
                                   [addr] + list(args), kwargs)
    runner = ApplicationRunner(server, realm)
    runner.run(session, auto_reconnect=True)


class ControlClientSession(ApplicationSession):

    def __init__(self, config, script, script_args, script_kwargs):
        ApplicationSession.__init__(self, config)
        self.script = (script, script_args, script_kwargs)

    def onConnect(self):
        self.log.info('transport connected')
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        self.log.info('authentication challenge received')

    # The Operations API...

    def onLeave(self, details):
        self.log.info('session left: {}'.format(details))
        self.disconnect()

    def onDisconnect(self):
        self.log.info('transport disconnected')
        try:
            reactor.stop()
        except ReactorNotRunning:
            pass

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info('session joined: {}'.format(details))
        script, a, kw = self.script
        yield from script(self, *a, **kw)
        yield self.leave()



class OperationClient:
    """The endpoint client is associated with a single operation rather
    than with an operation server."""

    def __init__(self, app, root_address, op_name):
        self.app = app
        self.root = root_address
        self.op_name = op_name
        
    def request(self, action, params=None, timeout=None):
        return self.app.call(self.root + '.ops', action, self.op_name,
                             params=params, timeout=timeout)

    def status(self, params=None):
        return self.request('status', params=params)

    def start(self, params=None):
        return self.request('start', params=params)

    def wait(self, params=None, timeout=None):
        return self.request('wait', params=params, timeout=timeout)

class TaskClient(OperationClient):
    def abort(self, params=None):
        return self.request('abort', params=params)

class ProcessClient(OperationClient):
    def stop(self, params=None):
        return self.request('stop', params=params)
