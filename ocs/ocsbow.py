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

def main_launch(args):
    # This is specifically for starting the host master agent process;
    # that's different than starting the host master's main process
    # (see start/stop for that).

    # Parse the config to find this host's HostMaster instance info.
    site, host, instance = ocs.site_config.get_config(args, 'HostMaster')

    if args.command in ['unlaunch', 'relaunch']:
        print('Trying to stop HostMaster agent...')
        master_addr = '%s.%s' % (site.hub.data['address_root'],
                                 instance.data['instance-id'])
        client = ocs.site_config.get_control_client(
            instance.data['instance-id'], args=args)
        try:
            stat = client.request('start', 'die', [])
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host master at %s' % master_addr)
                print('That probably means the Agent is not running.')
            else:
                print('Unexpected error getting master process status:')
                raise

    if args.command in ['launch', 'relaunch']:
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

def main_masterproc(args):
    # Parse the config to find this host's HostMaster instance info.
    site, host, instance = ocs.site_config.get_config(args, 'HostMaster')

    # Connect to crossbar.
    master_addr = '%s.%s' % (site.hub.data['address_root'], instance.data['instance-id'])

    client = cw.ControlClient(
        master_addr,
        url=site.hub.data['wamp_server'],
        realm=site.hub.data['wamp_realm'])
    try:
        client.start()
    except ConnectionRefusedError as e:
        print('Failed to establish connection to crossbar server.')
        print('  url: %s' % site.hub.data['wamp_server'])
        print('  realm: %s' % site.hub.data['wamp_realm'])
        sys.exit(1)

    # Subscriptions?
    if args.command == 'monitor' or args.follow:
        last_msg = 0.
        def monitor_func(*args, **kwargs):
            # This is a general monitoring function that just prints
            # whatever was sent.  Most pubsub sources output
            # structured information (such as Operation Session
            # blocks) so we can eventually tailor the output to the
            # topic.
            global last_msg
            topic = kwargs.get('meta', {}).get('topic', '(unknown)')
            print('==%s== : ' % topic, args)
            last_msg = time.time()

        feed_addr = master_addr + '.feed'
        client.subscribe(feed_addr, monitor_func)

    try:
        if args.command == 'status':
            stat = client.request('status', 'master', [])
        elif args.command == 'start':
            stat = client.request('start', 'master', [])
        elif args.command == 'stop':
            stat = client.request('stop', 'master', [])
        else:
            stat = None

        if stat is not None:
            # Decode stat
            err, msg, session = stat
            if err != ocs.OK:
                print('Error when requesting master Process "%s":\n  %s' %
                      (args.command, msg))
            print('Status of the master Process: %s' % session['status'])

        if args.command == 'stop' and err == ocs.OK:
            # Block for it to exit.
            print('Waiting for exit...')
            stat = client.request('wait', 'master', timeout=5)
            err, msg, session = stat
            if err == ocs.TIMEOUT:
                print(" ... timed-out!  Last status report is: %s" % session['status'])
            elif err == ocs.OK:
                print(" ... done.")
            else:
                print(" ... Error! : %s" % msg)

        elif args.command == 'monitor' or args.follow:
            session = None
            try:
                while True:
                    if last_msg is not None and time.time() - last_msg > 5:
                        print('[Blocking for logs; Ctrl-C to exit.]')
                        last_msg = None
                    time.sleep(5)
            except KeyboardInterrupt:
                pass

        if session is not None:
            n_trunc = 20
            print('Most recent session log (truncated to %i lines):' % n_trunc)
            for msg in session.get('messages',[])[-n_trunc:]:
                print('  %.3f' % msg[0], msg[1])



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
    elif args.command in ['crossbar']:
        main_crossbar(args)
    elif args.command in ['launch', 'unlaunch', 'relaunch']:
        main_launch(args)
    elif args.command in ['status', 'start', 'stop', 'monitor']:
        main_masterproc(args)
