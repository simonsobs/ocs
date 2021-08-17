import argparse
import sys
import code
import readline, rlcompleter

try:
    import IPython
    use_ipython = True
except ImportError:
    use_ipython = False

from ocs.matched_client import MatchedClient
from ocs import site_config, base

DESCRIPTION = """
This script provides a quick way to start a python or ipython shell to
interact with an OCS Agent.  You will need to set OCS_CONFIG_DIR
environment variable to the directory containing default.yaml, or else
use --site-* options to specify your configuration.

If you know the instance-id of the Agent you want to talk to, run::

  %(prog)s shell INSTANCE_ID

If you want to query the registry for a list of Agents, run::

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
        dest='command', metavar='command', help=
        "Command (\"%(prog)s {command} -h\" for more help)")

    # shell
    p = client_sp.add_parser('shell', help=
                             "Start an interactive python session with "
                             "a MatchedClient instantiated.")
    p.add_argument('instance_id', nargs='*', help=
                   "E.g. aggregator or fakedata-1.  Pass more than one to "
                   "get multiple clients.")
    p.add_argument('--simple', action='store_true', help=
                   "Do not use ipython for the shell, even if it is "
                   "available.")

    # scan
    p = client_sp.add_parser('scan', help=
                             "Gather and print list of registered Agents.")
    p.add_argument('--details', action='store_true', help=
                   "Show the running 'status' of all operations.")

    return parser

def get_instance_id(full_address, args):
    prefix = args.address_root + '.'
    assert(full_address.startswith(prefix))
    return full_address[len(prefix):]

def scan(parser, args):
    if args.site_http is None:
        parser.error('Unable to find the OCS config; set OCS_CONFIG_DIR?')

    reg_addr = args.registry_address
    if reg_addr is None:
        reg_addr = 'registry'
    c = MatchedClient(get_instance_id(reg_addr, args), args=args)

    # Get agent list.
    status = c.main.status()
    info = status.session['data']
    print(f'List of Registered Agents: ({len(info)})')
    for addr, data in info.items():
        try:
            instance_id = get_instance_id(addr, args)
        except:
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

    cs = [MatchedClient(iid, args=args) for iid in args.instance_id]
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
    else:
        parser.error(f"Unknown command '{args.command}'")
