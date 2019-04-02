"""This modules supports the command-line script "ocsbow".

At the time of this writing, only the argparse bit has been moved in,
to assist with autodoc in sphinx.

"""

import ocs

import argparse
import os

DESCRIPTION="""This is the high level control script for ocs.  Its principal uses
are to inspect the local host's site configuration file, and to start
and communicate with the HostMaster Agent for the local host."""

def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = ocs.site_config.add_arguments(parser)
    parser.add_argument('--follow', '-f', action='store_true')
    cmdsubp = parser.add_subparsers(dest='command')

    # config
    p = cmdsubp.add_parser('config', help=
                           'Query the local OCS config.')
    p.add_argument('cfg_request', nargs='?', choices=['summary', 'plugins', 'crossbar'],
                   default='summary')

    # crossbar
    p = cmdsubp.add_parser('crossbar', help=
                           'Manipulate the local crossbar router.')
    p.add_argument('cb_request', choices=['start', 'stop', 'status',
                                          'generate_config'], help=
                   'Use these commands to start, stop, or request status '
                   'from the local crossbar server, if such configuration '
                   'is described in the host config.  The generate_config '
                   'sub-command can be used to produce a crossbar JSON '
                   'configuration file consistent with the parameters in '
                   'the host config.')
    p.add_argument('--fg', action='store_true', default=False,
                   help='If request is "start", run in foreground rather '
                   'than spawning to background.')

    # hostmaster agent instance
    p = cmdsubp.add_parser('launch', help=
                           'Launch an instance of the HostMaster agent.')

    p = cmdsubp.add_parser('relaunch', help=
                           'Unlaunch then Launch the HostMaster agent.')

    p = cmdsubp.add_parser('unlaunch', help=
                           'Unlaunch, i.e. cause to exit, the running HostMaster agent.')

    p = cmdsubp.add_parser('monitor', help=
                           'Connect to the HostMaster log feed and copy to '
                           'the terminal.')

    # start, stop
    p = cmdsubp.add_parser('start', help=
                           'Start the HostMaster agent.')
    p = cmdsubp.add_parser('stop', help=
                           'Stop the HostMaster agent.')
    p = cmdsubp.add_parser('status', help=
                           'Show status of the HostMaster agent.')
    
    return parser

def render_crossbar_config_example(pars):
    """Returns the text of a basic crossbar config file, suitable for OCS
    use.
    
    """
    _pars = {
        'realm': 'debug_realm',
        'address_root': 'observatory',
        'port': 8001,
    }
    _pars.update(pars)
    
    # Generate configuration file.
    template_file = os.path.join(os.path.split(ocs.__file__)[0],
                                 'support/crossbar_config.json')
    config_text = open(template_file).read()

    # Manual substitution, since json contains many { formatting chars }.
    for k, v in _pars.items():
        config_text = config_text.replace('{'+k+'}', str(v))

    return config_text
