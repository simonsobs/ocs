"""This module supports the command-line script "ocsbow".

ocsbow is used to launch and communicate with the HostMaster agent.

"""

import ocs
from ocs import client_http

import argparse
import difflib
import os
import sys
import time

DESCRIPTION="""This is the high level control script for ocs.  Its principal uses
are to inspect the local host's site configuration file, and to start
and communicate with the HostMaster Agent for the local host."""

class OcsbowError(Exception):
    pass

def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = ocs.site_config.add_arguments(parser)
    cmdsubp = parser.add_subparsers(dest='command')

    # basic catch-alls
    p = cmdsubp.add_parser('status', help=
                           'Show status of the HostMaster.')
    p = cmdsubp.add_parser('up', help=
                           'Start everything on the target host.')
    p = cmdsubp.add_parser('down', help=
                           'Stop everything on the target host.')

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
        assert(text.startswith('wamp.') or text.startswith('client_http.'))
    except Exception as e:
        return False, args, str(args)
    return True, text, str(data)

def print_config(args):
    site, host, _ = ocs.site_config.get_config(args, '*host*')
    if args.cfg_request == 'summary':
        print('ocs configuration summary')
        print('-------------------------')
        print()
        print('ocs import led to: %s' % (ocs.__file__))
        print()
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
        print('Configuration for the OCS hub:')
        print(site.hub.summary())
        print()
        print('Configuration for crossbar service on this host (%s):' % host.name)
        if host.crossbar is None:
            print('  Not configured.')
        else:
             print(host.crossbar.summary())
        print()


def generate_crossbar_config(hm):
    cb_filename = './config.json'
    if hm.crossbar is None:
        print('There is no crossbar entry in this host config.\n\n'
              'A crossbar configuration cannot be generated without this info.')
        return False
    if hm.crossbar.cbdir is None:
        print('The crossbar config-dir is not set in this host config.\n\n'
              'Using %s as the target output file.\n' % cb_filename)
    else:
        cb_filename = os.path.join(hm.crossbar.cbdir, 'config.json')
        print('The crossbar config-dir is set to:\n  %s\n'
              'Using\n  %s\nas the target output file.\n' % 
              (hm.crossbar.cbdir, cb_filename))

    print('Generating crossbar config text.')
    config_text = hm.generate_crossbar_config()

    if os.path.exists(cb_filename):
        lines0 = open(cb_filename).readlines()
        lines1 = config_text.splitlines(keepends=True)
        if lines0 == lines1:
            print('No changes to %s are needed.' % cb_filename)
        else:
            print('\nThe target output file differs from the new one:')
            diff = difflib.unified_diff(
                lines0, lines1,fromfile=cb_filename, tofile='new')
            for line in diff:
                print(line, end='')
            print('\n')
            print('To adopt the new config, remove %s and re-run me.' % cb_filename)
    else:
        open(cb_filename, 'w').write(config_text)
        print('Wrote %s' % cb_filename)

class HostMasterManager:
    def __init__(self, args):
        """Note we save and use a reference to args... if it's modified,
        reinstantiate me..

        """
        # site, host, instance configs.
        self.args = args
        self.SHI = ocs.site_config.get_config(args, 'HostMaster')
        site, host, instance = self.SHI
        self.crossbar = host.crossbar

        self.master_addr = '%s.%s' % (site.hub.data['address_root'],
                                 instance.data['instance-id'])
        self.working_dir = args.working_dir
        try:
            self.client = ocs.site_config.get_control_client(
                instance.data['instance-id'], args=args)
        except ConnectionError:
            self.client = None

    def generate_crossbar_config(self):
        site, host, instance = self.SHI
        import urllib
        urld = urllib.parse.urlparse(site.hub.data['wamp_server'])
        pars = {
            'realm': site.hub.data['wamp_realm'],
            'address_root': site.hub.data['address_root'],
            'port': urld.port,
        }
        return render_crossbar_config_example(pars)

    def crossbar_action(self, cb_cmd, foreground=False):
        # Start / stop / check the crossbar server.
        cmd = self.crossbar.get_cmd(cb_cmd)
        if cb_cmd == 'start' and not foreground:
            # Unless user specifically requests foreground (blocking),
            # send crossbar start to the background.  But leave error
            # logging on, because start-up issues (such as trying to
            # start when another session is already active) will
            # otherwise be annoying to diagnose.
            cmd.extend(['--loglevel', 'error'])
            flags = os.P_NOWAIT
            monitor_time = 2.
        else:
            # For stop and status and sometimes start, run crossbar in
            # the foreground.
            flags = os.P_WAIT
            monitor_time = None

        pid = os.spawnv(flags, cmd[0], cmd)
        if monitor_time is not None:
            time.sleep(monitor_time)
            try:
                os.kill(pid, 0)
                print('New crossbar instance running as pid %i' % pid)
            except OSError:
                print('New crossbar instance exited within %.1f seconds.' % monitor_time)
                sys.exit(10)

    def status(self):
        """Try to get the status of the master Process.  This will indirectly
        tell us whether the HostMaster agent is running, too.

        Returns a dictionary with elements:

        - 'success' (bool): indicates only that the requests completed
          without error, and that the other reported results can be
          trusted.
        - 'agent_running' (bool)
        - 'master_process_running' (bool)
        - 'message' (string): Text you can report to "the user".

        """
        result = {
            'success': True,
            'crossbar_running': False,
            'agent_running': False,
            'master_process_running': False,
            'message': ''}
        if self.client is None:
            result['message'] = 'Could not connect to crossbar.'
            return result
        else:
            result['crossbar_running'] = True

        try:
            stat = self.client.request('status', 'master')
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                result['message'] = (
                    'Failed to contact host master at %s; that probably means '
                    'that the HostMaster Agent is not running.' % self.master_addr)
            elif parsed and err_name == 'client_http.error.connection_error':
                result['message'] = (
                    'Connection error: %s; probably crossbar is down.' % text)
                result['crossbar_running'] = False
                return result
            elif parsed and err_name == 'client_http.error.request_error':
                result['message'] = (
                    'Request error: %s; perhaps crossbar not configured for http.' % text)
                result['crossbar_running'] = True
                return result
            else:
                print(parsed, err_name)
                print('Unhandled exception when querying status.', file=sys.stderr)
                raise
        else:
            result['agent_running'] = True
            ok, msg, session = stat
            if ok == ocs.OK:
                status_text = session.get('status', '<unknown>')
                is_running = (status_text == 'running')
                result['master_process_running'] = is_running
                if is_running:
                    result['message'] = (
                        'Master Process has been running for %i seconds.' %
                        (time.time()  - session['start_time']))
                    result['child_states'] = session['data']
                else:
                    result['message'] = 'Master Process is in state: %s' % status_text
            else:
                result['Unexpected error querying master Process status: %s' % msg]
                result['ok'] = False
        return result

    def stop(self, check=True, timeout=5.):
        print('Trying to stop HostMaster agent...')
        try:
            stat = self.client.request('start', 'die')
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host master at %s' % self.master_addr)
                print('That probably means the Agent is not running.')
            else:
                print('Unexpected error getting master process status:')
                raise
        if not check:
            return True, 'Agent exit requested.'
        stop_time = time.time() + timeout
        try:
            ok, msg, session = self.client.request('wait', 'die', timeout=timeout)
            if not ok:
                return False, 'Agent "die" Task reported an error: %s' % msg
            while time.time() < stop_time:
                status = self.status()
                if not status['agent_running']:
                    return True, 'Agent has exited and relinquished registrations.'
                time.sleep(.1)
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name in ['wamp.error.no_such_procedure',
                                       'wamp.error.canceled']:
                return True, 'Agent has exited and relinquished registrations.'
        return False, 'Agent did not die within %.1f seconds.' % timeout

    def start(self, check=True, timeout=5., up=False):
        site, host, instance = self.SHI
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
               '--quiet',
               '--site-file', site.source_file,
               '--site-host', host.name,
               '--working-dir', self.working_dir]
        if up:
            cmd.extend(['--initial-state', 'up'])

        print('Launching host_master (%s)...' % cmd[1])
        pid = os.spawnv(os.P_NOWAIT, cmd[0], cmd)
        print('... pid is %i' % pid)
        if check:
            stop_time = time.time() + timeout
            while time.time() < stop_time:
                status = self.status()
                if status['agent_running']:
                    return True, 'Agent is running and registered.'
                time.sleep(.1)
            return False, 'Agent did not register within %.1f seconds.' % timeout
        return True, 'Agent launched.'

    def agent_control(self, request, targets):
        # Parse the config to find this host's HostMaster instance info.
        site, host, instance = ocs.site_config.get_config(self.args, 'HostMaster')

        client = ocs.site_config.get_control_client(
                instance.data['instance-id'], args=self.args)

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
            feed_addr = self.master_addr + '.feed'
            client.subscribe(feed_addr, monitor_func)

        try:
            # In all cases, make sure process is running.
            stat = client.request('status', 'master')
            err, msg, session = stat
            master_proc_running = (session.get('status') == 'running')

            if request == 'status':
                if not master_proc_running:
                    print('The master Process is not running.')
                else:
                    print('The master Process is running.')
                    print('In the future, I will tell you about what child '
                          'Agents are detected / active.')
                return

            if request == 'start':
                params = {'requests': [(t, 'up') for t in targets]}
            elif request == 'stop':
                params = {'requests': [(t, 'down') for t in targets]}
            elif request == 'restart':
                params = {'requests': [(t, 'cycle') for t in targets]}

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
                      (request, msg))

        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host master at %s' % self.master_addr)
                sys.exit(1)
            print('Unexpected error getting master process status:')
            raise


def print_status(stat):
    print('Status:\n'
          '  crossbar connection ok: {0[crossbar_running]}\n'
          '  HostMaster agent found: {0[agent_running]}\n'
          '  Master Process running: {0[master_process_running]}\n'
          .format(stat))
    if 'child_states' in stat:
        fmt = '  {child_id:30} {next_action:>20} {target_state:>20}'
        print(fmt.format(child_id='[child-identifier]',
                         next_action='[current_state]',
                         target_state='[target_state]'))
        for d in stat['child_states']:
            print(fmt.format(child_id=d['class_name']+'::'+d['instance_id'], **d))
        print()


def main():
    parser = get_parser()

    args = parser.parse_args()
    if args.working_dir is None:
        args.working_dir = os.getcwd()
    ocs.site_config.reparse_args(args, '*host*')

    if args.command == 'config':
        return print_config(args)

    # Other actions will need some form of...
    hm = HostMasterManager(args)

    if args.command == 'crossbar':
        if args.cb_request == 'generate_config':
            generate_crossbar_config(hm)
        else:
            hm.crossbar_action(args.cb_request, args.fg)

    elif args.command == 'hostmaster':
        status_info = hm.status()
        is_running = status_info['agent_running']
        do_stop = is_running and args.hm_request in ['stop', 'restart']
        do_start = ((not is_running and args.hm_request == 'start') or
                    (args.hm_request == 'restart'))
        ok, msg = True, ''
        if do_stop:
            ok, msg = hm.stop()

        if ok and do_start:
            ok, msg = hm.start()

        if not ok:
            raise OcsbowError(msg)

    elif args.command == 'agent':
        hm.agent_control(args.agent_request, args.target)

    elif args.command == 'status':
        stat = hm.status()
        print_status(stat)

    elif args.command == 'up':
        stat = hm.status()
        if not stat['crossbar_running']:
            print('Trying to start crossbar...')
            hm.crossbar_action('start')
            # Re-instantiate.
            hm = HostMasterManager(args)
            stat = hm.status()
        if not stat['crossbar_running']:
            raise OcsbowError('Failed to start crossbar!')
        # And the agent...
        if not stat['agent_running']:
            print('Trying to launch hostmaster agent...')
            ok, message = hm.start(up=True)
            if not ok:
                raise OcsbowError('Failed to start master process: %s' % message)
        # Reinforce that we want all child agents up, now.
        stat = hm.status()
        if not all([c['target_state']=='up' for c in stat.get('child_states', [])]):
            hm.agent_control('start', ['all'])
            time.sleep(2) # Master Process has a 1 second sleep, so we
                          # need to wait even longer here.
        stat = hm.status()
        print_status(stat)

    elif args.command == 'down':
        # Stop the agent.
        stat = hm.status()
        if stat['agent_running']:
            print('Requesting HostMaster termination.')
            hm.stop()
        if hm.crossbar is not None:
            if stat['crossbar_running']:
                print('Stopping crossbar.')
                hm.crossbar_action('stop')
            else:
                print('No running crossbar detected, system is already "down".')
        hm = HostMasterManager(args)
        stat = hm.status()
        print_status(stat)
