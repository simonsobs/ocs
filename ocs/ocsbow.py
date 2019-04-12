"""This module supports the command-line script "ocsbow".

ocsbow is used to launch and communicate with the HostMaster agent.

"""

import ocs
from ocs import client_wampy as cw

import argparse
import os
import sys
import time

DESCRIPTION="""This is the high level control script for ocs.  Its principal uses
are to inspect the local host's site configuration file, and to start
and communicate with the HostMaster Agent for the local host."""

def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = ocs.site_config.add_arguments(parser)
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
    p = cmdsubp.add_parser('hostmaster', help=
                           'Manipulate the local HostMaster agent instance.')

    p.add_argument('hm_request', choices=['start', 'stop', 'restart', 'status'],
                   help=
                   'Use these commands to start, stop, restart, or request '
                   'status from the HostMaster Agent instance.')

    # agent-set
    p = cmdsubp.add_parser('agent', help=
                           'Manipulate child Agent instances controlled by the HostMaster.')

    p.add_argument('agent_request', choices=['start','stop','restart','status'],
                   help='Use these commands to start, stop, or request the '
                   'status of individual Agents controlled by the HostMaster.')

    p.add_argument('target', nargs='*', default=['all'], help=
                   'Agent instance_id to which the command should be applied.')

    # up, down.
    p = cmdsubp.add_parser('up', help=
                           'Start EVERYTHING.')
    p = cmdsubp.add_parser('down', help=
                           'Stop EVERYTHING.')
    p = cmdsubp.add_parser('status', help=
                           'Show status of EVERYTHING.')
    
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

def decode_exception(args):
    """
    Decode certain RuntimeError raised by wampy.
    """
    try:
        text, data = args[0][4:6]
        assert(text.startswith('wamp.'))
    except Exception as e:
        return False, args, str(args)
    return True, text, str(data)

def main_config(args):
    if args.cfg_request == 'summary':
        print('ocs configuration summary')
        print('-------------------------')
        print()
        print('ocs import led to: %s' % (ocs.__file__))
        print()
        site, host, _ = ocs.site_config.get_config(args, '*host*')
        print('Site file was determined to be: %s' % site.source_file)
        print()
        print('Logging directory is: %s' % host.log_dir)
        print('The site file describes %i hosts:' % len(site.hosts))
        for k,v in site.hosts.items():
            print('  Host %s includes %i agent instances:' % (k, len(v.instances)))
            for inst in v.instances:
                print('    %s::%s' % (inst['agent-class'], inst['instance-id']))
            print()

    if args.cfg_request == 'plugins':
        print('ocs plugin detection')
        print('--------------------')
        print('Scanning.')
        site, host, _  = ocs.site_config.get_config(args, '*host*')
        for p in host.agent_paths:
            print('  ... adding to path: %s' % p)
            sys.path.append(p)
        ocs.site_config.scan_for_agents()
        print('Found:')
        for k,v in ocs.site_config.agent_script_reg.items():
            print('  %-20s : %s' % (k,v))
        print()

    if args.cfg_request == 'crossbar':
        print('ocs crossbar configuration')
        print('--------------------------')
        print()
        site, host, _  = ocs.site_config.get_config(args, '*host*')
        print('Configuration for the OCS hub:')
        print(site.hub.summary())
        print()
        print('Configuration for crossbar service on this host (%s):' % host.name)
        if host.crossbar is None:
            print('  Not configured.')
        else:
            print(host.crossbar.summary())
        print()

def main_crossbar(args):
    site, host, instance = ocs.site_config.get_config(args, '*host*')

    if args.cb_request == 'generate_config':
        import urllib
        urld = urllib.parse.urlparse(site.hub.data['wamp_server'])
        pars = {
            'realm': site.hub.data['wamp_realm'],
            'address_root': site.hub.data['address_root'],
            'port': urld.port,
        }
        print('Writing crossbar config to stdout...', file=sys.stderr)
        print(render_crossbar_config_example(pars))
        text = '\n'
        if host.crossbar is None:
            text += 'There is no crossbar entry in this host config.\n\n'
        else:
            if host.crossbar.cbdir is None:
                text += 'The crossbar config-dir is not set in this host config.\n\n'
            else:
                text += ('The crossbar config-dir is set to "%s";\nthe config '
                         'text should be copied to the file config.json in '
                         'that directory.\n' % host.crossbar.cbdir)
        print(text, file=sys.stderr)
    else:
        # Start / stop / check the crossbar server.
        cmd = host.crossbar.get_cmd(args.cb_request)
        flags = os.P_WAIT
        monitor_time = None
        if args.cb_request == 'start' and not args.fg:
            # By default, we launch to background.  We leave error logging
            # on, because start-up issues (such as trying to start when
            # another session is already active) will otherwise be
            # annoying to diagnose.
            cmd.extend(['--loglevel', 'error'])
            flags = os.P_NOWAIT
            monitor_time = 2.
        print('Executing: ', cmd)
        pid = os.spawnv(flags, cmd[0], cmd)
        if monitor_time is not None:
            time.sleep(monitor_time)
            try:
                os.kill(pid, 0)
                print('New crossbar instance running as pid %i' % pid)
            except OSError:
                print('New crossbar instance exited within %.1f seconds.' % monitor_time)
                sys.exit(10)

def main_hostmaster(args):
    # This is specifically for starting/stopping/restarting the host
    # master agent; that's different than starting the host master's
    # main Process (see agent start/stop for that).

    # Parse the config to find this host's HostMaster instance info.
    site, host, instance = ocs.site_config.get_config(args, 'HostMaster')

    master_addr = '%s.%s' % (site.hub.data['address_root'],
                             instance.data['instance-id'])
    client = ocs.site_config.get_control_client(
        instance.data['instance-id'], args=args)

    if args.hm_request == 'status':
        print('Getting status of HostMaster agent...')
        try:
            stat = client.request('status', 'master')
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host master at %s' % master_addr)
                print('That probably means the Agent is not running.')
            else:
                print('Unexpected error getting master process status:')
                raise
        else:
            ok, msg, session = stat
            if ok == ocs.OK:
                status_text = session.get('status', '<unknown>')
                if status_text == 'running':
                    status_text += ' for %i seconds' % \
                        (time.time()  - session['start_time'])
                print('Master Process is:', status_text)
            else:
                print('Error requesting master Process status: %s' % msg)
                return

    if args.hm_request in ['stop', 'restart']:
        print('Trying to stop HostMaster agent...')
        try:
            stat = client.request('start', 'die')
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host master at %s' % master_addr)
                print('That probably means the Agent is not running.')
            else:
                print('Unexpected error getting master process status:')
                raise

    if args.hm_request in ['start', 'restart']:
        log_dir = host.log_dir
        if log_dir is not None and not log_dir.startswith('/'):
            log_dir = os.path.join(host.working_dir, log_dir)
        if log_dir is not None:
            if not os.path.exists(log_dir):
                print('\nWARNING: the expected log dir, %s, does not exist!\n' %
                      log_dir)
        # Most important is the site filename and host alias.
        hm_script = os.path.join(host.agent_paths[0], 'host_master/host_master.py')
        print('Launching HostMaster through %s' % hm_script)
        print('Log dir is: %s' % log_dir)
        cmd = [sys.executable, hm_script,
               '--site-file', site.source_file,
               '--site-host', host.name,
               '--working-dir', args.working_dir]
        print('Launching host_master (%s)...' % cmd[1])
        pid = os.spawnv(os.P_NOWAIT, cmd[0], cmd)
        print('... pid is %i' % pid)

def main_agent(args):
    # Parse the config to find this host's HostMaster instance info.
    site, host, instance = ocs.site_config.get_config(args, 'HostMaster')

    client = ocs.site_config.get_control_client(
            instance.data['instance-id'], args=args)
    master_addr = '%s.%s' % (site.hub.data['address_root'], instance.data['instance-id'])

    if 0:
        # Subscriptions?
        # Keeping this, disabled, as a place-holder.  It can be used
        # to subscribe to log feeds from arbitrary agents.
        #
        def monitor_func(*args, **kwargs):
            # This is a general monitoring function that just prints
            # whatever was sent.  Most pubsub sources output
            # structured information (such as Operation Session
            # blocks) so we can eventually tailor the output to the
            # topic.
            topic = kwargs.get('meta', {}).get('topic', '(unknown)')
            print('==%s== : ' % topic, args)
        feed_addr = master_addr + '.feed'
        client.subscribe(feed_addr, monitor_func)

    try:
        # In all cases, make sure process is running.
        stat = client.request('status', 'master')
        err, msg, session = stat
        master_proc_running = (session.get('status') == 'running')

        if args.agent_request == 'status':
            if not master_proc_running:
                print('The master Process is not running.')
            else:
                print('The master Process is running.')
                print('In the future, I will tell you about what child '
                      'Agents are detected / active.')
            return

        if args.agent_request == 'start':
            params = {'requests': [(t, 'up') for t in args.target]}
        elif args.agent_request == 'stop':
            params = {'requests': [(t, 'down') for t in args.target]}
        elif args.agent_request == 'restart':
            params = {'requests': [(t, 'cycle') for t in args.target]}

        if not master_proc_running:
            print('Starting master process.')
            # If starting process for the first time, set all agents
            # to 'down'.
            params['requests'].insert(0, ('all', 'down'))
            err, msg, session = \
                client.request('start', 'master', params)
        else:
            err, msg, session = \
                client.request('start', 'update', params)

        if err != ocs.OK:
            print('Error when requesting master Process "%s":\n  %s' %
                  (args.agent_request, msg))
        print('Status of the master Process: %s' % session['status'])

    except RuntimeError as e:
        parsed, err_name, text = decode_exception(e.args)
        if parsed and err_name == 'wamp.error.no_such_procedure':
            print('Failed to contact host master at %s' % master_addr)
            sys.exit(1)
        print('Unexpected error getting master process status:')
        raise

    client.stop()


def main():
    parser = get_parser()

    args = parser.parse_args()
    if args.working_dir is None:
        args.working_dir = os.getcwd()
    ocs.site_config.reparse_args(args, '*host*')

    if args.command == 'config':
        main_config(args)
    elif args.command == 'crossbar':
        main_crossbar(args)
    elif args.command == 'hostmaster':
        main_hostmaster(args)
    elif args.command == 'agent':
        main_agent(args)
