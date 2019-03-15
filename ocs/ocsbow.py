"""This modules supports the command-line script "ocsbow".

At the time of this writing, only the argparse bit has been moved in,
to assist with autodoc in sphinx.

"""


import ocs

import argparse

DESCRIPTION="""This is the high level control script for ocs.  Its principal uses
are to inspect the local host's site configuration file, and to start
and communicate with the HostMaster Agent for the local host."""

def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = ocs.site_config.add_arguments(parser)
    parser.add_argument('command', choices=['config', 'plugins', 'status',
                                            'monitor',
                                            'launch',
                                            'start', 'stop'])
    parser.add_argument('--follow', '-f', action='store_true')
    return parser
