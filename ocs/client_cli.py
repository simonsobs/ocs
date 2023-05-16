import argparse
import sys
import code
import readline
import rlcompleter
import re

try:
    import IPython
    use_ipython = True
except ImportError:
    use_ipython = False

try:
    from twisted.internet import reactor, defer
    from autobahn.wamp.types import SubscribeOptions
    from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
    use_twisted = True
except ModuleNotFoundError:
    use_twisted = False

from ocs.ocs_client import OCSClient
from ocs import site_config, base

DESCRIPTION = """
This script provides a quick way to start a python or ipython shell to
interact with an OCS Agent.  You will need to set OCS_CONFIG_DIR
environment variable to the directory containing default.yaml, or else
use --site-* options to specify your configuration.

If you know the instance-id of the Agent you want to talk to, run::

  %(prog)s shell INSTANCE_ID

If you want to listen to heartbeat feeds to get a list of Agents in
the system, run::

  %(prog)s scan

"""


def get_parser():
    # What you put into description vs. usage vs. help is rather
    # subtle ... if making edits, confirm that "ocs-client-cli -h" and
    # "ocs-client-cli command -h" both render nicely.
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    client_sp = parser.add_subparsers(
        dest='command', metavar='command', help="Command (\"%(prog)s {command} -h\" for more help)")

    # shell
    p = client_sp.add_parser('shell', help="Start an interactive python session with "
                             "an OCSClient instantiated.")
    p.add_argument('instance_id', nargs='*', help="E.g. aggregator or fakedata-1.  Pass more than one to "
                   "get multiple clients.")
    p.add_argument('--simple', action='store_true', help="Do not use ipython for the shell, even if it is "
                   "available.")

    # scan
    p = client_sp.add_parser('scan', help="Gather and print list of Agents.")
    p.add_argument('--details', action='store_true', help="List all Operations with their current status OpCode.")
    p.add_argument('--use-registry', nargs='?', const='registry', help="Query the registry (faster than listening for heartbeats). "
                   "Pass the registry instance_id as an argument (default to 'registry').")

    # scan
    p = client_sp.add_parser('listen', help="Subscribe to feed(s) and dump to stdout.")
    p.add_argument('feed_selector', help="Feed name, which can include wildcard matching (double "
                   " ..).  E.g., try 'observatory..feeds.heartbeat'")

    return parser

# Note there's a similar function to this in ocsbow ... consider
# combining effort...


def decode_exception(args):
    """Decode exceptions from WAMP http interface."""
    try:
        text, data = args[0][4:6]
        assert (text.startswith('wamp.') or text.startswith('client_http.'))
    except Exception:
        return False, args, str(args)
    return True, text, str(data)


def get_instance_id(full_address, args):
    prefix = args.address_root + '.'
    assert (full_address.startswith(prefix))
    return full_address[len(prefix):]


def listen(parser, args):
    if not use_twisted:
        parser.error('The "listen" function requires twisted and autobahn packages.')
    feeds = args.feed_selector
    print(f'Subscribing to {feeds}')

    class Listener(ApplicationSession):
        @defer.inlineCallbacks
        def onJoin(self, details):
            topic = feeds
            options = SubscribeOptions(match='wildcard', details=True)
            yield self.subscribe(self.on_event, topic, options=options)

        def on_event(self, msg, details=None):
            print(f'[{details.topic}] {msg}')

        def onDisconnect(self):
            if reactor.running:
                reactor.stop()

    url = args.site_hub
    realm = args.site_realm
    runner = ApplicationRunner(url, realm)
    runner.run(Listener)


def scan(parser, args):
    if args.site_http is None:
        parser.error('Unable to find the OCS config; set OCS_CONFIG_DIR?')

    if args.use_registry:
        reg_addr = f'{args.address_root}.{args.use_registry}'
        try:
            c = OCSClient(get_instance_id(reg_addr, args), args=args)
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                parser.error(
                    f'Failed to connect to registry at {reg_addr}; the registry '
                    'must be running for "scan" to work.')
            else:
                raise e
        status = c.main.status()
        info = status.session['data']
        adjective = 'Registered'

    else:
        if not use_twisted:
            parser.error('The "scan" function requires twisted and autobahn '
                         'unless --use-registry is passed.')
        beats = {}

        class Listener(ApplicationSession):
            @defer.inlineCallbacks
            def onJoin(self, details):
                topic = f'{args.address_root}..feeds.heartbeat'
                options = SubscribeOptions(match='wildcard', details=True)
                yield self.subscribe(self.on_event, topic, options=options)

            def on_event(self, msg, details=None):
                beats[details.topic] = msg

            def onDisconnect(self):
                if reactor.running:
                    reactor.stop()

        url = args.site_hub
        realm = args.site_realm
        runner = ApplicationRunner(url, realm)

        print('Listening to heartbeat feeds for 2 seconds ...')
        reactor.callLater(2.0, reactor.stop)
        runner.run(Listener)
        # Un-log
        if hasattr(sys, '__stdout__'):
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        # Convert to resemble registry format.  Originally, heartbeat
        # data was just the integer 0; then with OpCode it became a
        # dict mapping op_name -> op_code value.
        info = {}
        for k, v in beats.items():
            instance_id = re.search(f'{args.address_root}.(.*).feeds.heartbeat', k)[1]
            if not isinstance(v[0], dict):
                v[0] = {'old_agent_no_opcodes': base.OpCode.EXPIRED}
            info[instance_id] = {'op_codes': v[0]}
        adjective = 'Detected'

    # Get agent list.
    print(f'List of {adjective} Agents: ({len(info)})')
    for addr, data in info.items():
        try:
            instance_id = get_instance_id(addr, args)
        except BaseException:
            instance_id = addr
        print(f'  {instance_id}')
        if args.details:
            for k, v in data['op_codes'].items():
                vs = base.OpCode(v).name
                print(f'    {k:20}: {vs}')
    print()


def shell(parser, args):
    if len(args.instance_id) == 0:
        parser.error('No instance_id provided.')

    cs = [OCSClient(iid, args=args) for iid in args.instance_id]
    vars = {'clients': cs}

    if len(cs) > 1:
        banner = 'ocs-client-cli --\n'
        for i, iid in enumerate(args.instance_id):
            banner += "  -- use clients[%i].<op_name> to talk to %s\n" % (i, iid)

    else:
        banner = "ocs-client-cli -- use client.<op_name> to talk to %s" % args.instance_id[0]
        vars['client'] = cs[0]

    if use_ipython and not args.simple:
        # IPython interpreter
        IPython.embed(header=banner, user_ns=vars, colors='linux')
    else:
        # Standard interpreter with tab-completion.
        readline.set_completer(rlcompleter.Completer(vars).complete)
        readline.parse_and_bind("tab: complete")
        code.InteractiveConsole(vars).interact(banner=banner)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = get_parser()

    # Note this call adds a bunch of args to the parser, and parses them
    # including looking up the site config file and loading defaults from
    # there.
    args = site_config.parse_args(agent_class='*control*',
                                  parser=parser, args=args)

    if args.command == 'scan':
        scan(parser, args)
    elif args.command == 'shell':
        shell(parser, args)
    elif args.command == 'listen':
        listen(parser, args)
    else:
        parser.error(f"Unknown command '{args.command}'")
