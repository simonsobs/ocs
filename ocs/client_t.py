import ocs

import txaio
txaio.use_twisted()

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ReactorNotRunning

from autobahn.wamp.types import ComponentConfig
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
import deprecation


@deprecation.deprecated(
    deprecated_in='v0.6.1',
    details="Renamed to run_control_script"
)
def run_control_script2(*args, **kwargs):
    run_control_script(*args, **kwargs)


def run_control_script(function, parser=None, *args, **kwargs):
    """
    Run a function in a ControlClientSession, within a site_config
    paradigm, assuming that additional configuration will be passed
    through command line arguments.

    Args:
        function: The function to call.

        parser: argparse.ArgumentParser, with control script options
            pre-loaded.  If None, this will be created internally in
            the usual way.

    The command line is parsed and site configuration information is
    loaded.  The WAMP server information is used to configure the
    Control Client's connection before launching the function.  The
    function is invoked as::

        function(app, parser_args, *args, **kwargs)

    where app is the ControlClientSession and parser_args is the
    argparse.Namespace object including processing done by
    ocs.site_config.  Note that the observatory root_address is
    contained in parser_args.root_address.  Any additional arguments
    defined in the parser will also be present.

    This function can be invoked with parser=None, or else with a
    parser that has been initialized for control client purposes, like
    this::

        from ocs import client_t, site_config
        parser = site_control.add_arguments()  # initialized ArgParser
        parser.add_option('--target')          # Options for this client
        client_t.run_control_script2(my_script, parser=parser)

    In the my_script function, use parser_args.target to get the
    target.
    """
    if parser is None:
        parser = ocs.site_config.add_arguments()
    pargs = parser.parse_args()
    ocs.site_config.reparse_args(pargs, '*control*')
    server, realm = pargs.site_hub, pargs.site_realm
    session = ControlClientSession(ComponentConfig(realm, {}), function,
                                   [pargs] + list(args), kwargs)
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
