"""This module supports the command-line script "ocsbow".

ocsbow is used to launch and communicate with the HostMaster agent.

"""

import ocs
from ocs import matched_client, client_http

import argparse
import difflib
import os
import sys
import time
import urllib

DESCRIPTION="""This is the high level control script for ocs.  Its principal uses
are to inspect the local host's site configuration file, and to start
and communicate with the HostMaster Agent for the local host."""

# agent_class of the HostMaster.
HOSTMASTER_CLASS = 'HostMaster'

class OcsbowError(Exception):
    pass

def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    cmdsubp = parser.add_subparsers(dest='command')

    # basic catch-alls
    p = cmdsubp.add_parser('status', help=
                           'Show status of the HostMaster.')
    p.add_argument('--host', '-H', default=None, action='append',
                   help='Limit hosts that are displayed.')
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

def get_args_and_site_config(args=None):
    # The proper parsing of args in all the various cases is pretty
    # arcane, so do it once, here.  So this will decode the args, and
    # also return a site_config (site, host, instance) such that:
    #
    # - If ocsbow finds a config file but the active host is not in
    #   the config file, only "site" is not None.
    # - If the active host is in the config file, host will be populated.
    # - If this active host has a HostManager configured, instance
    #   will also be set up.
    #
    if args is None:
        args = sys.argv[1:]
    for agent_class in ['*host*', '*control*']:
        try:
            parser = get_parser()
            args_ = ocs.site_config.parse_args(agent_class=agent_class, parser=parser)
            site_config = ocs.site_config.get_config(args_, agent_class=agent_class)
            break
        except KeyError:
            pass
    if agent_class == '*host*':
        # Promote to HM instance?
        try:
            site_config = ocs.site_config.get_config(
                args_, agent_class=HOSTMASTER_CLASS)
        except RuntimeError:
            pass

    return args_, site_config

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

def crossbar_test(args, site_config):
    """Test connection to the crossbar bridge.  Returns (ok, msg)."""
    site, host, instance = site_config
    client = client_http.ControlClient(
        '%s._crossbar_check_' % site.hub.data['address_root'],
        url=site.hub.data['wamp_http'], realm=site.hub.data['wamp_realm'])
    try:
        client.call(client.agent_addr)
    except client_http.ControlClientError as ccex:
        suberr = ccex.args[0][4]
        if suberr == 'client_http.error.connection_error':
            ok, msg = False, 'http bridge not found at {wamp_http}.'
        elif suberr == 'wamp.error.no_such_procedure':
            ok, msg = True, 'http bridge reached at {wamp_http}.'
        else:
            ok, msg = True, 'unexpected bridge connection problem; raised %s' % (str(ccex))
    return ok, msg.format(**site.hub.data)

def print_status(args, site_config):
    site, host, instance = site_config

    cb_ok, msg = crossbar_test(args, site_config)

    print('ocs status')
    print('----------')
    print()
    print('The site config file is :\n  %s' % site.source_file)
    print()
    print('The crossbar base url is :\n  %s' % site.hub.data['wamp_http'])
    if not cb_ok:
        print('  ****Warning**** %s' % msg)
    print()

    for host_name, host_data in site.hosts.items():
        if args.host is not None and host_name not in args.host:
            continue
        hms = []
        rows = []
        blank_state = {'current': '?',
                       'target': '?'}
        for idx, inst in enumerate(host_data.instances):
            inst = inst.copy()
            inst.update(blank_state)
            if inst['agent-class'] == HOSTMASTER_CLASS:
                sort_order = 0
                hms.append(HostMasterManager(
                    args, site_config, instance_id=inst['instance-id']))
            else:
                sort_order = ['x', 'yes', 'no', 'docker'].index(
                    inst.get('manage', 'yes'))
            rows.append((sort_order, idx, inst))
        rows.sort()
        agent_info = {k['instance-id']: k for _, _, k in rows}
        for hm in hms:
            info = hm.status()
            cinfo = {
                'target': 'n/a',
            }
            if info['master_process_running']:
                cinfo['current'] = 'up'
            elif info['agent_running']:
                cinfo['current'] = 'sleeping'
            elif info['crossbar_running']:
                cinfo['current'] = 'down'
            else:
                cinfo['current'] = '?'
            agent_info[hm.instance_id].update(cinfo)

            for cinfo in info['child_states']:
                this_id = cinfo['instance_id']
                if this_id not in agent_info:
                    agent_info[this_id] = {
                        'instance-id': this_id,
                        'agent-class': 'docker',
                    }
                    agent_info[this_id].update(blank_state)
                agent_info[this_id].update({
                    'current': cinfo['next_action'],
                    'target': cinfo['target_state']
                })
        header = {'instance-id': '[instance-id]',
                  'agent-class': '[agent-class]',
                  'current': '[state]',
                  'target': '[target]'}
        field_widths = {'instance-id': 30,
                        'agent-class': 20}
        if len(agent_info):
            field_widths = {k: max(v0, max([len(v[k]) for v in agent_info.values()]))
                            for k, v0 in field_widths.items()}
        fmt = '  {instance-id:%i} {agent-class:%i} {current:>10} {target:>10}' % (
            field_widths['instance-id'], field_widths['agent-class'])
        header = fmt.format(**header)
        print('-' * len(header))
        print(f'Host: {host_name}\n')
        print(header)
        for v in agent_info.values():
            print(fmt.format(**v))
        print()

def print_config(args, site_config):
    site, host, instance = site_config

    if args.cfg_request == 'summary':
        print('ocs configuration summary')
        print('-------------------------')
        print()
        print('ocs import led to:\n  %s' % (ocs.__file__))
        print()
        print('Site file was determined to be:\n  %s' % site.source_file)
        print()
        if host is None:
            print('No configuration block was found for the specified host.')
        else:
            print('Specified host is:  %s\n' % host)
        print()
        print('The site file describes %i hosts:' % len(site.hosts))
        for k,v in site.hosts.items():
            print('  Host %s includes %i agent instances:' % (k, len(v.instances)))
            for inst in v.instances:
                print('    %s::%s' % (inst['agent-class'], inst['instance-id']))
            print()

    if args.cfg_request == 'plugins':
        if host is None:
            print('Specified site-host is not found in site config.')
            return False
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
        if host is None or host.crossbar is None:
            print('This host is not known to the site config.')
        else:
            print('Configuration for crossbar service on this host (%s):' % host.name)
            print(host.crossbar.summary())
        print()


def generate_crossbar_config(cm, site_config):
    cb_filename = './config.json'
    if cm is None:
        print('There is no crossbar entry in this host config.\n\n'
              'A crossbar configuration cannot be generated without this info.')
        return False
    if cm.crossbar.cbdir is None:
        print('The crossbar config-dir is not set in this host config.\n\n'
              'Using %s as the target output file.\n' % cb_filename)
    else:
        cb_filename = os.path.join(cm.crossbar.cbdir, 'config.json')
        print('The crossbar config-dir is set to:\n  %s\n'
              'Using\n  %s\nas the target output file.\n' % 
              (cm.crossbar.cbdir, cb_filename))

    print('Generating crossbar config text.')
    site = site_config.site
    urld = urllib.parse.urlparse(site.hub.data['wamp_server'])
    pars = {
        'realm': site.hub.data['wamp_realm'],
        'address_root': site.hub.data['address_root'],
        'port': urld.port,
    }
    config_text = render_crossbar_config_example(pars)

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

class CrossbarManager:
    def __init__(self, args, host):
        if host.crossbar is None:
            raise RuntimeError('There is no crossbar entry in this host config.')
        self.crossbar = host.crossbar

    def action(self, cb_cmd, foreground=False):
        # Start / stop / check the crossbar server.
        if self.crossbar is None:
            print('There is no crossbar entry in this host config.\n')
            sys.exit(10)

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


class HostMasterManager:
    def __init__(self, args, site_config, instance_id=None):
        """Note we save and use a reference to args... if it's modified,
        reinstantiate me..

        """
        # site, host, instance configs.
        self.args = args
        self.site_config = site_config
        site, host, instance = self.site_config
        if instance_id is None:
            instance_id = instance.data['instance-id']
        self.instance_id = instance_id

        if instance is not None:
            self.master_addr = '%s.%s' % (site.hub.data['address_root'],
                                          instance.data['instance-id'])
        self.working_dir = args.working_dir
        try:
            self.client = ocs.matched_client.MatchedClient(instance_id, args=args)
        except (ConnectionError, client_http.ControlClientError):
            self.client = None

    def status(self):
        """Try to get the status of the master Process.  This will indirectly
        tell us whether the HostMaster agent is running, too.

        Returns a dictionary with elements:

        - 'success' (bool): indicates only that the requests completed
          without error, and that the other reported results can be
          trusted.
        - 'crossbar_running' (bool)
        - 'agent_running' (bool)
        - 'master_process_running' (bool)
        - 'child_states' (list)
        - 'message' (string): Text you can report to "the user".

        """
        result = {
            'success': True,
            'crossbar_running': False,
            'agent_running': False,
            'master_process_running': False,
            'child_states': [],
            'message': ''}
        if self.client is None:
            result['message'] = 'Could not connect to crossbar.'
            return result
        else:
            result['crossbar_running'] = True

        try:
            stat = self.client.master.status()
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
                    result['child_states'] = session['data']['child_states']
                else:
                    result['message'] = 'Master Process is in state: %s' % status_text
            else:
                result['Unexpected error querying master Process status: %s' % msg]
                result['ok'] = False
        return result

    def stop(self, check=True, timeout=5.):
        print('Trying to stop HostMaster agent...')
        try:
            stat = self.client.die.start()
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
            ok, msg, session = self.client.die.wait(timeout=timeout)
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
        host = self.site_config.host
        log_dir = host.log_dir
        if log_dir is not None and not log_dir.startswith('/'):
            log_dir = os.path.join(host.working_dir, log_dir)
        if log_dir is not None:
            if not os.path.exists(log_dir):
                print('\nWARNING: the expected log dir, %s, does not exist!\n' %
                      log_dir)
        # Most important is the site filename and host alias.
        for agent_path in host.agent_paths:
            hm_script = os.path.join(agent_path, 'host_master/host_master.py')
            if os.path.exists(hm_script):
                break
        else:
            return False, "Could not find host_master.py in the agent_paths!"

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
        site, host, instance = ocs.site_config.get_config(self.args, HOSTMASTER_CLASS)

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


def main(args=None):
    args, site_config = get_args_and_site_config(args)
    site, host, instance = site_config

    if args.working_dir is None:
        args.working_dir = os.getcwd()

    if args.command is None:
        args.command = 'status'
        args.host = None

    if args.command == 'config':
        return print_config(args, site_config)

    hm, cm = None, None
    if instance is not None:
        hm = HostMasterManager(args, site_config)
    if host is not None and host.crossbar is not None:
        cm = CrossbarManager(args, host)

    if args.command == 'crossbar':
        if args.cb_request == 'generate_config':
            generate_crossbar_config(cm, site_config)
        elif cm is not None:
            cm.action(args.cb_request, args.fg)
        else:
            raise OcsbowError(
                'The site config does not describe a managed '
                'crossbar instance for this host.')

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
        print_status(args, site_config)

    elif args.command == 'up':
        stat = hm.status()
        if not stat['crossbar_running']:
            print('Trying to start crossbar...')
            cm.action('start')
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
        if cm is not None:
            if stat['crossbar_running']:
                print('Stopping crossbar.')
                cm.action('stop')
            else:
                print('No running crossbar detected, system is already "down".')
        hm = HostMasterManager(args)
        stat = hm.status()
        print_status(stat)
