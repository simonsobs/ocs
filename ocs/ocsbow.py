"""This module supports the command-line scripts "ocsbow" and
"ocsbow-local-support".

"""

import ocs
from ocs import client_http, ocs_client

import argparse
import difflib
import os
import subprocess as sp
import sys
import time
import urllib

DESCRIPTION = """ocsbow is used to talk to HostManager agents across an OCS
installation.  In a distributed OCS, you can request that Agents
across the observatory be started or stopped.

"""
EPILOG = """
More info for each command is available by adding --help, e.g. "ocsbow up --help".

For more details, see https://ocs.readthedocs.io/en/main/user/cli_tools.html#ocsbow.
"""

# agent_class of the HostManager.
HOSTMANAGER_CLASS = 'HostManager'


class OcsbowError(Exception):
    pass


def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     epilog=EPILOG)
    cmdsubp = parser.add_subparsers(
        dest='command', description="""
        For more information and options pertinent to a subcommand,
        add --help (e.g., "ocsbow up --help").""")

    # status
    p = cmdsubp.add_parser(
        'status', help='Display OCS status.',
        description="""

        Status information is obtained by querying all HostManagers
        described in the local version of the site config file.  The
        output is tabulated by host, and lists each agent reported as
        being managed by the HostManager (which may include agents not
        listed in the local copy of the site config).""")
    p.add_argument('--host', '-H', default=None, action='append',
                   help='Limit hosts that are displayed.')
    p.add_argument('--reload-config', '-r', default=None, action='store_true',
                   help='Request each HM to reprocess the site config file.')

    # common args for up and down
    target_parser = argparse.ArgumentParser(add_help=False)
    target_parser.add_argument(
        '--all', '-a', action='store_true', help="Apply the command to all HostManagers in the OCS.")
    target_parser.add_argument(
        '--dry-run', action='store_true', help="If set, HostManagers will be queried for info but no state "
        "change requests will be issued.")
    target_parser.add_argument(
        'instance', nargs='*', help="instance-id to target.  If this is the id of a HostManager "
        "agent, it will be asked to start all of its managed agents.")

    # up and down
    p = cmdsubp.add_parser('up', parents=[target_parser], help="Mark targets as 'up' (so HostManagers will "
                           "launch them).")
    p = cmdsubp.add_parser('down', parents=[target_parser], help="Mark targets as 'down' (so HostManagers will "
                           "shut them down).")

    # config
    p = cmdsubp.add_parser('config', help='Query the local OCS config.')
    p.add_argument('cfg_request', nargs='?', choices=['summary', 'plugins', 'crossbar'],
                   default='summary')

    return parser


def get_args_and_site_config(args=None, parser_func=None):
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
    if parser_func is None:
        parser_func = get_parser
    if args is None:
        args = sys.argv[1:]
    for agent_class in ['*host*', '*control*']:
        try:
            parser = parser_func()
            args_ = ocs.site_config.parse_args(agent_class=agent_class, parser=parser, args=args)
            site_config = ocs.site_config.get_config(args_, agent_class=agent_class)
            break
        except KeyError:
            pass
    if agent_class == '*host*':
        # Promote to HM instance?
        try:
            site_config = ocs.site_config.get_config(
                args_, agent_class=HOSTMANAGER_CLASS)
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
        config_text = config_text.replace('{' + k + '}', str(v))

    return config_text


def decode_exception(args):
    """
    Decode certain RuntimeError raised by wampy.
    """
    try:
        text, data = args[0][4:6]
        assert (text.startswith('wamp.') or text.startswith('client_http.'))
    except Exception:
        return False, args, str(args)
    return True, text, str(data)


def crossbar_test(args, site_config):
    """Test connection to the crossbar bridge.  Returns (ok, msg)."""
    site, host, instance = site_config
    client = client_http.ControlClient(
        '%s._crossbar_check_' % site.hub.data['address_root'],
        url=site.hub.data['wamp_http'], realm=site.hub.data['wamp_realm'])
    try:
        # This is not expected to succeed, but the different errors
        # tell us different things...
        client.call(client.agent_addr)
    except client_http.ControlClientError as ccex:
        suberr = ccex.args[0][4]
        if suberr == 'wamp.error.no_such_procedure':
            # This indicates we got through to the bridge, it liked
            # the realm and our address_root.  Return True.
            ok, msg = True, 'http bridge reached at {wamp_http}.'.format(**site.hub.data)
        elif suberr == 'client_http.error.connection_error':
            # Possibly crossbar server is not running.
            ok, msg = False, 'http bridge not found at {wamp_http}.'.format(**site.hub.data)
        elif suberr == 'wamp.error.not_authorized':
            # This is likely a configuration issue, print a banner and reraise it.
            print('***** crossbar / ocs configuration mismatch *****')
            print('The exception here indicates a likely configuration mismatch issue')
            print('with the crossbar server and OCS.  Specifically, the WAMP realm and')
            print('the OCS address_root must match between the site config file')
            print('and the crossbar config.')
            print('*****\n')
            raise ccex
        else:
            # I think this case hasn't been encountered much.
            print('***** unhandled error case *****\n')
            raise ccex
    return ok, msg


def get_status(args, site_config, restrict_hosts=None, reload_config=False):
    """Assemble a detailed description of the site configuration, that
    goes somewhat beyond what's in the site config by querying each
    HostManager it finds to identify docker-based or other secret
    Agents.  Return an absurd but informative structure that we dare
    not describe here.

    """
    site, host, instance = site_config
    cb_ok, msg = crossbar_test(args, site_config)
    output = {
        'crossbar': {
            'ok': cb_ok,
            'msg': msg,
        },
        'hosts': [],
        'warnings': [],
    }

    all_instance_ids = []
    warn_reloads = False
    warn_consistency = False

    # Loop over hosts found in the SCF ...
    for host_name, host_data in site.hosts.items():
        if restrict_hosts is not None and host_name not in restrict_hosts:
            continue
        hms = []
        agent_info = {}
        sort_order = ['hm', 'host', 'docker', 'ignore', 'other']

        # Loop over agent instances described in the SCF for this host.
        # This should result in agent_info entries with keys:
        # - instance-id  (already present)
        # - agent-class  (already present)
        # - manage       (may be present)
        # - sort-token
        # - agent-class-note (includes modifiers such as [d])
        # - agent-class-hm (agent-class-note from HM placeholder)
        # - current (current state place-holder for HM)
        # - target (target state place-holder for HM)

        for idx, inst in enumerate(host_data.instances):
            inst = inst.copy()

            # Fill in defaults ...
            try:
                inst['manage'] = ocs.site_config.InstanceConfig \
                                                ._MANAGE_MAP[inst.get('manage')]
            except KeyError:
                # Not a known 'manage' setting.
                pass

            inst.update({
                'agent-class-note': inst['agent-class'],
                'agent-class-hm': '?',
                'current': '?',
                'target': '?',
                'sort-token': sort_order[-1],
            })

            # Set sort-token and record HMs.
            if inst['agent-class'] == HOSTMANAGER_CLASS:
                inst['manage'] = 'hm'
                hms.append(HostManagerManager(
                    args, site_config, instance_id=inst['instance-id']))
            _st = inst['manage'].split('/')[0]  # hm, host, docker, ignore
            if _st in sort_order:
                inst['sort-token'] = _st

            # Modify agent-class name to get table-ready version; this
            # should be the same string HM status returns, later.
            if inst['sort-token'] == 'docker':
                inst['agent-class-note'] += '[d]'
            elif inst['sort-token'] == 'hm':
                inst['agent-class-hm'] = inst['agent-class-note']
            elif inst['sort-token'] in ['ignore', 'other']:
                # Mark as "unmanaged"; hotwire -hm value to match.
                inst['agent-class-note'] += '[unman]'
                inst['agent-class-hm'] = inst['agent-class-note']

            iid = inst['instance-id']
            if iid in all_instance_ids:
                output['warnings'].append(
                    f'***WARNING -- site config contains multiple entries '
                    f'with instance-id={iid}; ignoring all but first.')
                continue
            agent_info[iid] = inst
            all_instance_ids.append(iid)

        # Are we supposed to refresh_config these?
        if reload_config and len(hms):
            print('Requesting config reloads ...')
            for hm in hms:
                if hm.reload_config():
                    print(f'  Ok on {hm.instance_id}.')
                else:
                    print(f'  !! Failed on {hm.instance_id}.')
                    warn_reloads = True
            print()

        # Now loop through HostManagers and see what they know
        for hm in hms:
            info = hm.status()

            # Stow some info about the HostMan itself...
            cinfo = {
                'target': 'n/a',
            }
            if info['manager_process_running']:
                cinfo['current'] = 'up'
            elif info['agent_running']:
                cinfo['current'] = 'sleeping'
            elif info['crossbar_running']:
                cinfo['current'] = 'down'
            else:
                cinfo['current'] = '?'
            agent_info[hm.instance_id].update(cinfo)

            # Enrich agent_info using HostManager records.  This
            # updates (perhaps):
            # - next_action
            # - target_state
            # - class_name_display
            #
            # Generally one of three things can happen:
            #
            # 1. The HM instance-id is matched to the SCF, and the
            #    agent_class / execution method (docker etc) agree.
            # 2. The HM instance-id is matched to SCF, but with
            #    different class/method.
            # 3. The HM reports an instance-id that is not known to
            #    the SCF (or at least not on this host).
            #
            # In the latter two cases, the agent-class-show will
            # display the two discrepant values, between /, with a '?'
            # for a missing thing.

            found = []
            for cinfo in info['child_states']:
                this_id = cinfo['instance_id']
                if this_id in found:
                    output['warnings'].append(
                        f'***WARNING -- HostManager {hm.instance_id}reports '
                        f'multiple states for instance-id={this_id}; '
                        'ignoring all but first.')
                    continue
                found.append(this_id)

                if this_id in agent_info:
                    inst = agent_info[this_id]
                    inst['agent-class-hm'] = cinfo['agent_class']
                else:
                    # Create a record for this unknown instance.
                    _m = 'host'
                    if '[d' in cinfo['agent_class']:
                        _m = 'docker'
                    inst = {
                        'instance-id': this_id,
                        'agent-class': '?',
                        'agent-class-note': '?',
                        'agent-class-hm': cinfo['agent_class'],
                        'manage': _m,
                        'sort-token': _m,
                    }
                    agent_info[this_id] = inst

                inst['target'] = cinfo['target_state']
                if cinfo['next_action'] != 'down' and \
                   cinfo['stability'] <= 0.5:
                    inst['current'] = 'unstable'
                else:
                    inst['current'] = cinfo['next_action']

        # Populate the agent-class-show.
        for k, v in agent_info.items():
            a, b = v['agent-class-note'], v['agent-class-hm']
            v['agent-class-show'] = a
            if a != b:
                v['agent-class-show'] = '%s/%s' % (a, b)
                warn_consistency = True

        # Sort the agent_info dict.
        sorted_keys = sorted([(sort_order.index(v['sort-token']), k)
                              for k, v in agent_info.items()])
        agent_info = {k: agent_info[k] for _, k in sorted_keys}

        output['hosts'].append({
            'host_name': host_name,
            'hostmanager_count': len(hms),
            'agent_info': agent_info})

    if warn_reloads:
        output['warnings'].append(
            '***WARNING -- failed to request reload_config on some HostManagers.')

    if warn_consistency:
        output['warnings'].append(
            '***WARNING -- where agent-class value contains a slash (/) it '
            'indicates an inconsistency between the local Site Config '
            '(pre-slash) and HostManager reported (post-slash) Agent '
            'Class values.')

    return output


def print_status(args, site_config):
    site, host, instance = site_config

    status = get_status(args, site_config, restrict_hosts=args.host,
                        reload_config=args.reload_config)

    print('ocs status')
    print('----------')
    print()
    print('The site config file is :\n  %s' % site.source_file)
    print()
    print('The crossbar base url is :\n  %s' % site.hub.data['wamp_http'])
    if not status['crossbar']['ok']:
        print('  ****Warning**** %s' % status['crossbar']['msg'])
    print()

    for hstat in status['hosts']:
        header = {'instance-id': '[instance-id]',
                  'agent-class-show': '[agent-class]',
                  'current': '[state]',
                  'target': '[target]'}
        field_widths = {'instance-id': 20,
                        'agent-class-show': 30}
        if len(hstat['agent_info']):
            field_widths = {k: max(v0, max([len(v[k])
                                            for v in hstat['agent_info'].values()]))
                            for k, v0 in field_widths.items()}
        fmt = '  {instance-id:%i} {agent-class-show:%i} {current:>10} {target:>10}' % (
            field_widths['instance-id'], field_widths['agent-class-show'])
        header = fmt.format(**header)
        print('-' * len(header))
        print(f'Host: {hstat["host_name"]}\n')
        print(header)
        for v in hstat['agent_info'].values():
            print(fmt.format(**v))
        print()

    if len(status['warnings']):
        print('Important Notes:')
        for w in status['warnings']:
            print('  ' + w)
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
            print('Specified host is:  %s\n' % host.name)
        print()
        print('The site file describes %i hosts:' % len(site.hosts))
        for k, v in site.hosts.items():
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
        for k, v in ocs.site_config.agent_script_reg.items():
            print('  %-20s : %s' % (k, v))
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
                lines0, lines1, fromfile=cb_filename, tofile='new')
            for line in diff:
                print(line, end='')
            print('\n')
            print('To adopt the new config, remove %s and re-run me.' % cb_filename)
        print()
    else:
        open(cb_filename, 'w').write(config_text)
        print('Wrote %s' % cb_filename)
        print()


class CrossbarManager:
    def __init__(self, host):
        if host.crossbar is None:
            raise RuntimeError('There is no crossbar entry in this host config.')
        self.crossbar = host.crossbar

    def is_running(self):
        if self.crossbar is None:
            raise OcsbowError('There is no crossbar entry in this host config.')
        cmd = self.crossbar.get_cmd('status') + ['--assert=running']
        retcode = sp.call(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        return retcode == 0

    def action(self, cb_cmd, foreground=False):
        # Start / stop / check the crossbar server.
        if self.crossbar is None:
            raise OcsbowError('There is no crossbar entry in this host config.')

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


class HostManagerManager:
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
            self.manager_addr = '%s.%s' % (site.hub.data['address_root'],
                                           instance.data['instance-id'])
        self.working_dir = args.working_dir
        self._reconnect()

    def _reconnect(self):
        try:
            self.client = ocs_client.OCSClient(self.instance_id, args=self.args)
        except (ConnectionError, client_http.ControlClientError):
            self.client = None

    def status(self):
        """Try to get the status of the manager Process.  This will indirectly
        tell us whether the HostManager agent is running, too.

        Returns a dictionary with elements:

        - 'success' (bool): indicates only that the requests completed
          without error, and that the other reported results can be
          trusted.
        - 'crossbar_running' (bool)
        - 'agent_running' (bool)
        - 'manager_process_running' (bool)
        - 'child_states' (list)
        - 'message' (string): Text you can report to "the user".

        """
        result = {
            'success': True,
            'crossbar_running': False,
            'agent_running': False,
            'manager_process_running': False,
            'child_states': [],
            'message': ''}
        if self.client is None:
            result['message'] = 'Could not connect to crossbar.'
            return result
        else:
            result['crossbar_running'] = True

        try:
            stat = self.client.manager.status()
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                result['message'] = (
                    'Failed to contact host manager at %s; that probably means '
                    'that the HostManager Agent is not running.' % self.manager_addr)
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
                result['manager_process_running'] = is_running
                if is_running:
                    result['message'] = (
                        'Manager Process has been running for %i seconds.' %
                        (time.time() - session['start_time']))
                    result['child_states'] = session['data'].get('child_states', [])
                else:
                    result['message'] = 'Manager Process is in state: %s' % status_text
            else:
                result['Unexpected error querying manager Process status: %s' % msg]
                result['ok'] = False
        return result

    def stop(self, check=True, timeout=5.):
        print('Trying to stop HostManager agent...')
        try:
            self.client.die.start()
        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host manager at %s' % self.manager_addr)
                print('That probably means the Agent is not running.')
            else:
                print('Unexpected error getting manager process status:')
                raise
        if not check:
            return True, 'Agent exit requested.'
        stop_time = time.time() + timeout
        try:
            ok, msg, session = self.client.die.wait(timeout=timeout)
            if not ok:
                return False, 'Agent "die" Task reported an error: %s' % msg
            while time.time() < stop_time:
                self._reconnect()
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

    def start(self, check=True, timeout=5., up=None, foreground=False):
        if self.instance_id is None:
            print('\nERROR: cannot "start" HostManager because '
                  'instance_id could not be determined.')
            return False, 'The HostManager instance_id is not known.'

        host = self.site_config.host
        log_dir = host.log_dir
        if log_dir is not None and not log_dir.startswith('/'):
            log_dir = os.path.join(host.working_dir, log_dir)
        if log_dir is not None:
            if not os.path.exists(log_dir):
                print('\nWARNING: the expected log dir, %s, does not exist!\n' %
                      log_dir)

        print('Log dir is: %s' % log_dir)

        # Most important args are instance_id, site filename and host
        # alias.
        cmd = [sys.executable,
               '-m', 'ocs.agents.host_manager.agent',
               '--instance-id', self.instance_id,
               '--site-file', self.site_config.site.source_file,
               '--site-host', host.name,
               '--working-dir', self.working_dir]
        if up is True:
            cmd.extend(['--initial-state', 'up'])
        if up is False:
            cmd.extend(['--initial-state', 'down'])
        if not foreground:
            cmd.extend(['--quiet'])

        print('Launching host_manager (%s)...' % cmd[1])
        if foreground:
            ret_val = sp.call(cmd)
            return True, "Agent exited with code %i" % ret_val
        pid = os.spawnv(os.P_NOWAIT, cmd[0], cmd)
        print('... pid is %i' % pid)
        if check:
            stop_time = time.time() + timeout
            while time.time() < stop_time:
                self._reconnect()
                status = self.status()
                if status['agent_running']:
                    return True, 'Agent is running and registered.'
                time.sleep(.1)
            return False, 'Agent did not register within %.1f seconds.' % timeout
        return True, 'Agent launched.'

    def reload_config(self):
        # Request a config reload.  Returns True if the request
        # succeeded.
        err, msg, session = self.client.update(reload_config=True)
        return (err == ocs.OK) and session['success']

    def agent_control(self, request, targets):
        try:
            # In all cases, make sure process is running.
            stat = self.client.manager.status()
            err, msg, session = stat
            manager_proc_running = (session.get('status') == 'running')

            if request == 'status':
                if not manager_proc_running:
                    print('The manager Process is not running.')
                else:
                    print('The manager Process is running.')
                    print('In the future, I will tell you about what child '
                          'Agents are detected / active.')
                return

            if request == 'up':
                params = {'requests': [(t, 'up') for t in targets]}
            elif request == 'down':
                params = {'requests': [(t, 'down') for t in targets]}

            if not manager_proc_running:
                print('Starting manager process.')
                # If starting process for the first time, set all agents
                # to 'down'.
                params['requests'].insert(0, ('all', 'down'))
                err, msg, session = \
                    self.client.manager.start(**params)
            else:
                known_children = [cs.get('instance_id')
                                  for cs in session['data']['child_states']]
                targets_not_found = [t for t in targets if t not in known_children]
                if len(targets_not_found):
                    print('Warning, some targets not known to HostManager: ')
                    print(f'  {targets_not_found}')
                    print('Requesting reload_config.')
                    params['reload_config'] = True

                err, msg, session = \
                    self.client.update.start(**params)

            if err != ocs.OK:
                print('Error when requesting manager Process "%s":\n  %s' %
                      (request, msg))

        except RuntimeError as e:
            parsed, err_name, text = decode_exception(e.args)
            if parsed and err_name == 'wamp.error.no_such_procedure':
                print('Failed to contact host manager at %s' % self.manager_addr)
                sys.exit(1)
            print('Unexpected error getting manager process status:')
            raise


def _term_format(text, indent='', right_margin=1):
    # Slowly reformat text to fit in the terminal ...
    output = ''
    line = indent
    limit = os.get_terminal_size()[0] - right_margin
    while len(text):
        # Always pop at least one word.
        try:
            idx = text.index(' ')
        except BaseException:
            idx = len(text)
        while idx < len(text) and text[idx] == ' ':
            idx += 1
        word = text[:idx]
        text = text[idx:]
        if len(line) + len(word.rstrip()) >= limit:
            output += line.rstrip() + '\n'
            line = indent + word
        elif len(line) + len(word) >= limit:
            output += line + word.rstrip() + '\n'
            line = indent
        else:
            line += word

    return output + line + '\n'


class LocalSupports:
    """This class helps with controlling crossbar and HostManager on the
    current host.  This is convenient in small setups in the absence
    of docker.

    """

    def __init__(self, args, site_config, update=True, target=None):
        self.args = args
        self.site_config = site_config
        self.target = target
        self.crossbar = {
            'manage': False,
        }
        self.host_manager = {
            'manage': False,
            'configured': False,
        }

        if site_config.host.crossbar is not None:
            self.crossbar['manage'] = True
            self.crossbar['ctrl'] = CrossbarManager(site_config.host)
        if site_config.instance is not None:
            self.host_manager['configured'] = True
            self.host_manager['manage'] = (site_config.instance.manage == 'yes')
        if update:
            self.update()

    def update(self):
        if self.crossbar['manage']:
            self.crossbar['running'] = self.crossbar['ctrl'].is_running()
        else:
            self.crossbar['running'] = 'n/a'
        self.crossbar['connection'] = crossbar_test(self.args, self.site_config)[0]

        if self.host_manager['configured']:
            hm = HostManagerManager(self.args, self.site_config)
            stat = hm.status()
            self.host_manager['ctrl'] = hm
            self.host_manager['instance-id'] = hm.instance_id
            self.host_manager['alive'] = stat['agent_running']
            self.host_manager['process'] = stat['manager_process_running']
        else:
            self.host_manager['instance-id'] = 'n/a'
            self.host_manager['alive'] = 'n/a'
            self.host_manager['process'] = 'n/a'

        # Possible solutions to each outage?
        if self.target is not None:
            self.analysis = [
                (self.target, 'Action requested for %s only.' % self.target)]
            return

        solutions = []
        if self.crossbar['connection']:
            # We seem to be connected ...
            if self.crossbar['manage'] and not self.crossbar['running']:
                solutions.append(('fatal', 'configuration problem! A connection '
                                  'to crossbar exists, but it does not appear to '
                                  'be the managed crossbar configured for this host.'))
        else:
            # We do not have a connection ...
            if self.crossbar['manage'] and not self.crossbar['running']:
                solutions.append(('crossbar', 'Crossbar is down, but should start if you '
                                  ' run "ocs-local-support start".'))
            else:
                solutions.append(('fatal', 'Cannot connect to crossbar. This host '
                                  'is not configured to manage crossbar, so start '
                                  'it up on the correct system.'))

        if self.host_manager['configured']:
            if not self.host_manager['alive']:
                if not self.crossbar['connection']:
                    solutions.append(('warning',
                                      'The HostManager might be running, but '
                                      'this could not be confirmed because no '
                                      'crossbar connection could be made.'))
                    solutions.append(('agent', 'Running "ocsbow here start" might '
                                      'start the Agent too.'))
                elif self.host_manager['manage']:
                    solutions.append(('agent', 'The HostManager is not running, but '
                                      'should start if you run "ocs-local-support start".'))
                else:
                    solutions.append(('fatal', 'The HostManager is not running, and '
                                      'is not managed by this systems.  Start '
                                      'it manually, or using systemd, or something.'))
            elif not self.host_manager['process']:
                solutions.append(('process', 'The HostManager manager process is not '
                                  'running, but should start if you run "ocs-local-support start".'))
        self.analysis = solutions

    def fail_on_missing_crossbar_config(self):
        """Check if crossbar is managed by this config.  If not, print
        error message and exit(1)."""
        if not self.crossbar['manage']:
            print('Error!  Crossbar config file not set.\n\n'
                  'To start crossbar or to generate a config file, the site '
                  'config file must have a "crossbar" entry; see docs.\n')
            sys.exit(1)


def main(args=None):
    args, site_config = get_args_and_site_config(args)
    site, host, instance = site_config

    if args.working_dir is None:
        args.working_dir = os.getcwd()

    if args.command is None:
        args.command = 'status'
        args.host = None
        args.reload_config = None

    if args.command == 'config':
        print_config(args, site_config)

    elif args.command == 'status':
        print_status(args, site_config)

    elif args.command in ['up', 'down']:
        # Common target processing ...
        hms = []
        agents = []
        status = get_status(args, site_config)
        for host_data in status['hosts']:
            active_hms = [v for v in host_data['agent_info'].values()
                          if v['agent-class'] == HOSTMANAGER_CLASS]
            others = [v for v in host_data['agent_info'].values()
                      if v['agent-class'] != HOSTMANAGER_CLASS]
            for inst in active_hms:
                if args.all or inst['instance-id'] in args.instance:
                    hms.append(inst)
            for inst in others:
                if inst['instance-id'] not in args.instance:
                    continue
                if inst['sort-token'] not in ['host', 'docker']:
                    raise OcsbowError(
                        "Cannot perform action on '%s', as it is not "
                        "configured as a managed Agent." % inst['instance-id'])
                if len(active_hms) != 1:
                    raise OcsbowError(
                        "Cannot perform action on '%s', as there are "
                        "%i HostManagers configured on host '%s'." % (
                            inst['instance-id'], len(active_hms), host_data['host_name']))
                agents.append((inst, active_hms[0]))
        if args.dry_run:
            print('[dry-run, no requests will be issued]')

        clients = {}

        def client(hm):
            iid = hm['instance-id']
            if iid not in clients:
                clients[iid] = HostManagerManager(args, site_config, iid)
            return clients[iid]

        if len(hms) == 0 and len(agents) == 0:
            print(f'No targets found matching "{args.instance}"')

        for hm in hms:
            print(f'  {args.command} hostmanager {hm["instance-id"]} all')
            if args.dry_run:
                continue
            client(hm).agent_control(args.command, ['all'])
        for ag, hm in agents:
            print(f'  {args.command} agent {ag["instance-id"]} via {hm["instance-id"]}')
            if args.dry_run:
                continue
            client(hm).agent_control(args.command, [ag['instance-id']])


#
# ocs-local-support
#
LOCAL_DESCRIPTION = """ocs-local-support is used to control a crossbar router and
HostManager agent on this host.

Examples::

  ocs-local-support status
  ocs-local-support start
  ocs-local-support stop

Or with a target subsystem::

  ocs-local-support stop crossbar
  ocs-local-support status agent
  ocs-local-support start process
"""

LOCAL_EPILOG = """For more details, see
https://ocs.readthedocs.io/en/main/user/cli_tools.html#ocs-local-support."""


def get_parser_local():
    p = argparse.ArgumentParser(description=LOCAL_DESCRIPTION,
                                epilog=LOCAL_EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('here_cmd', choices=['status', 'start', 'stop',
                                        'generate_crossbar_config'],
                   help="Command to apply to the targets.")
    p.add_argument('target', nargs='?', default=None, choices=['crossbar', 'agent', 'process'],
                   help='Operate on the specific subsystem only.')
    p.add_argument('--foreground', action='store_true', help="For targeted 'start', run the command in the foreground and "
                   "copy stdout/stderr to the terminal.")
    return p


def main_local(args=None):
    args, site_config = get_args_and_site_config(
        args, parser_func=get_parser_local)
    site, host, instance = site_config

    if host is None:
        print('The ocs site_config system could not find a host '
              'block for this host. Do you need to pass --site-host?')
        sys.exit(1)

    if args.working_dir is None:
        args.working_dir = os.getcwd()

    if args.here_cmd is None:
        args.here_cmd = 'status'
        args.crossbar = True
        args.agent = True
        args.target = None

    if args.here_cmd == 'restart':
        actions = ['stop', 'start', 'status']
    else:
        actions = [args.here_cmd]

    # Targeting with args.target is handled through
    # supports.analysis for start, and by eligible() for stop.
    supports = LocalSupports(args, site_config, update=False,
                             target=args.target)

    def eligible(subsys):
        return (args.target is None) or (args.target == subsys)

    for action in actions:
        if action == 'status':
            supports.update()
            C, H = supports.crossbar, supports.host_manager
            print('Status of local supports:')
            print(f'  crossbar managed on this host:       {C["manage"]}')
            print(f'    crossbar running?:                 {C["running"]}')
            print(f'    connection to server?:             {C["connection"]}')
            print()
            print(f'  hostmanager configured on this host: {H["configured"]}')
            print(f'    manageable by ocsbow?:             {H["manage"]}')
            print(f'    agent running?                     {H["alive"]}')
            print(f'    manager process running?:          {H["process"]}')
            print(f'    instance-id:                       {H["instance-id"]}')
            print()
            if len(supports.analysis):
                print('Advice:')
                for soln, text in supports.analysis:
                    print(_term_format(text, '    ', 4))

        elif action == 'start':
            supports.update()
            fatals = [text for soln, text in supports.analysis
                      if soln == 'fatal']
            if len(fatals):
                print('Trouble!')
                for text in fatals:
                    print(_term_format(text, '    ', 4))
                sys.exit(1)

            if any([soln == 'crossbar' for soln, text in supports.analysis]):
                supports.fail_on_missing_crossbar_config()
                print('Trying to start crossbar...')
                supports.crossbar['ctrl'].action('start', foreground=args.foreground)
                supports.update()  # refresh .analysis

            if any([soln == 'agent' for soln, text in supports.analysis]):
                print('Trying to launch hostmanager agent...')
                hm = supports.host_manager['ctrl']
                ok, message = hm.start(foreground=args.foreground)
                if not ok:
                    raise OcsbowError('Failed to start manager process: %s' % message)
                supports.update()  # refresh .analysis

            if any([soln == 'process' for soln, text in supports.analysis]):
                hm = supports.host_manager['ctrl']
                hm.agent_control('start', ['all'])
                time.sleep(2)

        elif action == 'stop':
            supports.update()
            # Stop the process.
            if supports.host_manager['configured']:
                hm = supports.host_manager['ctrl']
                if hm.client is None:
                    print('No connection to HostManager.')
                else:
                    if eligible('process'):
                        print('Stopping manager process ...')
                        hm.client.manager.stop()
                        hm.client.manager.wait(timeout=1)
                    if eligible('agent') and supports.host_manager['manage']:
                        print('Requesting HostManager termination.')
                        hm.stop()
            if eligible('crossbar') and supports.crossbar['manage']:
                if supports.crossbar['running']:
                    print('Stopping crossbar.')
                    supports.crossbar['ctrl'].action('stop')
                else:
                    print('No running crossbar detected, system is already "down".')

        elif action == 'generate_crossbar_config':
            supports.fail_on_missing_crossbar_config()
            cm = supports.crossbar['ctrl']
            generate_crossbar_config(cm, site_config)
