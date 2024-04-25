import ocs
from ocs import ocs_agent, site_config, agent_cli
from ocs.agents.host_manager import drivers as hm_utils

import time
import argparse

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn.twisted.util import sleep as dsleep

import os
import sys

VALID_TARGETS = ['up', 'down']

# "agent_class" value used for docker services that do not seem to
# have a corresponding SCF entry.
NONAGENT_DOCKER = '[docker]'


class HostManager:
    """
    This Agent is used to start and stop OCS-relevant services on a
    particular host.  If the HostManager is launched automatically when
    a system boots, it can then be used to start up the rest of OCS on
    that host (either automatically or on request).
    """

    def __init__(self, agent, docker_composes=[],
                 docker_service_prefix='ocs-'):
        self.agent = agent
        self.running = False
        self.database = {}  # key is instance_id (or docker service name).
        self.docker_composes = docker_composes
        self.docker_service_prefix = docker_service_prefix

    @inlineCallbacks
    def _get_local_instances(self):
        """Parse the site config and return a list of this host's Agent
        instances.

        Returns:
          success (bool): True if config was successfully scanned.
            False otherwise, indiating perhaps we should go into a bit
            of a lock down while operator sorts that out.
          agent_dict (dict): Maps instance-id to a dict describing the
            agent config.  The config is as contained in
            HostConfig.instances but where 'instance-id',
            'agent-class', and 'manage' are all guaranteed populated
            (and manage is a valid full description, e.g. "host/down").
          warnings: A list of strings, each of which corresponds to
            some problem found in the config.

        """
        warnings = []
        instances = {}

        # Load site config file.
        try:
            site, hc, _ = site_config.get_config(
                self.agent.site_args, '*host*')
            self.site_config_file = site.source_file
            self.host_name = hc.name
            self.working_dir = hc.working_dir
        except Exception as e:
            warnings.append('Failed to read site config file -- '
                            f'likely syntax error: {e}')
            return returnValue((False, instances, warnings))

        # Scan for agent scripts in (deprecated) script registry
        try:
            for p in hc.agent_paths:
                if p not in sys.path:
                    sys.path.append(p)
            site_config.scan_for_agents()
        except Exception as e:
            warnings.append('Failed to scan for old plugin agents -- '
                            f'likely plugin config problem: {e}')
            return returnValue((False, instances, warnings))

        # Gather managed items from site config.
        for inst in hc.instances:
            if inst['instance-id'] in instances:
                warnings.append(
                    f'Configuration problem, instance-id={inst["instance-id"]} '
                    f'has multiple entries.  Ignoring repeats.')
                continue
            if inst['agent-class'] == 'HostManager':
                inst['manage'] = 'ignore'
            else:
                # Make sure 'manage' is set, and valid.
                inst['manage'] = inst.get('manage', None)
                try:
                    inst['manage'] = site_config.InstanceConfig._MANAGE_MAP[inst['manage']]
                except KeyError:
                    warnings.append(
                        f'Configuration problem, invalid manage={inst["manage"]} '
                        f'for instance_id={inst["instance-id"]}.')
                    continue
            instances[inst['instance-id']] = inst
        returnValue((True, instances, warnings))
        yield

    @inlineCallbacks
    def _update_docker_services(self, session):
        """Parse the docker-compose.yaml files and return the current
        status of all services.  For any services matching
        self.database entries, the corresponding DockerContainerHelper
        is updated with the new info.

        Returns:
          docker_services (dict): state information for all detected
            services, keyed by the service name.

        """
        # Read services from all docker-compose files.
        docker_services = {}
        for compose in self.docker_composes:
            try:
                services = yield hm_utils.parse_docker_state(compose)
                this_ok = True
                this_msg = f'Successfully parsed {compose} and its service states.'
            except Exception as e:
                this_ok = False
                this_msg = (f'Failed to interpret {compose} and/or '
                            f'its service states: {e}')

            # Don't issue the same complaint more than once per minute or so
            compose_was_ok, timestamp, last_msg = self.config_parse_status.get(
                compose, (False, 0, ''))
            if (this_ok != compose_was_ok) \
               or (not this_ok and time.time() - timestamp > 60) \
               or (not this_ok and this_msg != last_msg):
                session.add_message(this_msg)
                self.config_parse_status[compose] = (this_ok, time.time(), this_msg)

            if this_ok:
                docker_services.update(services)

        # Update all docker things in the database.
        retirees = []
        assigned_services = []
        for key, instance in self.database.items():
            if instance['management'] != 'docker':
                continue

            service_name = instance['agent_script']
            service_data = docker_services.get(service_name)
            assigned_services.append(service_name)

            prot = instance.get('prot')
            if prot is None:
                if service_data is not None:
                    # Create a prot entry with the service info.
                    instance['prot'] = hm_utils.DockerContainerHelper(service_data)
                    instance['operable'] = True
                    if instance['agent_class'] != NONAGENT_DOCKER:
                        instance['agent_class'] = _clsname_tool(instance['agent_class'], '[d]')
            else:
                if service_data is not None:
                    prot.update(service_data)
                else:
                    # service_data is missing, but there used to be a
                    # service there.  Close it out.
                    instance['prot'] = None
                    instance['operable'] = False
                    if instance['agent_class'] == NONAGENT_DOCKER:
                        session.add_message(f'Deleting non-agent service {key}')
                        retirees.append(key)
                    else:
                        session.add_message(f'Marking missing service for {key}')
                        instance['agent_class'] = _clsname_tool(instance['agent_class'], '[d?]')

        # If a non-agent [docker] service has disappeared, there's no
        # reason to show it in a list, and no persistent state /
        # operations to worry about.  So just delete it.
        for r in retirees:
            self.database.pop(r)

        # Create entries for any new un-matched docker services.
        unassigned_services = set(docker_services.keys()) \
            .difference(assigned_services)
        for srv in unassigned_services:
            instance = hm_utils.ManagedInstance.init(
                management='docker',
                instance_id=srv,
                agent_class=NONAGENT_DOCKER,
                full_name=(f'[docker]:{srv}'))
            instance.update({
                'agent_script': srv,
                'operable': True,
            })
            service_data = docker_services[srv]
            instance['prot'] = hm_utils.DockerContainerHelper(service_data)

            self.database[srv] = instance
            # If it's up, leave it up.
            if service_data['running']:
                instance['target_state'] = 'up'
                instance['next_action'] = 'up'

        returnValue(docker_services)

    @inlineCallbacks
    def _reload_config(self, session):
        """This helper function is called by both the ``manager``
        Process at startup, and the ``update`` Task.

        The Site Config File is parsed and used to update the internal
        database of child instances.  Any previously unknown child
        Agent is added to the internal tracking database, and assigned
        whatever target state is specified for that instance.  Any
        previously known child Agent instance is not modified.

        If any child Agent instances in the internal database appear
        to have been removed from the SCF, then they are set to have
        target_state "down" and will be deleted from the database when
        that state is reached.

        """
        def retire(db_key):
            instance = self.database.get(db_key, None)
            if instance is None:
                return
            instance['management'] = 'retired'
            instance['at'] = time.time()
            instance['target_state'] = 'down'

        def _full_name(cls, iid):
            if cls != NONAGENT_DOCKER:
                cls, _ = _clsname_tool(cls)
            return f'{cls}:{iid}'

        def same_base_class(a, b):
            return _clsname_tool(a)[0] == _clsname_tool(b)[0]

        # Parse the site config.
        parse_ok, agent_dict, warnings = yield self._get_local_instances()
        for w in warnings:
            session.add_message(w)

        self.config_parse_status['[SCF]'] = (parse_ok, time.time(), ''.join(warnings))
        if not parse_ok:
            return warnings

        # Any agents in the database that are not listed in the latest
        # agent_dict should be immediately retired.  That includes
        # things that are suddenly marked as manage=no.  Ignore docker
        # non-agents.
        for iid, instance in self.database.items():
            if instance['agent_class'] != NONAGENT_DOCKER and (
                    iid not in agent_dict or agent_dict[iid].get('manage') == 'ignore'):
                session.add_message(
                    f'Retiring {instance["full_name"]}, which has disappeared from '
                    f'configuration file(s) or has manage:no.')
                retire(iid)

        # Create / update entries for every agent in the host
        # description, unless it is explicitly marked as ignore.
        for iid, hinst in agent_dict.items():
            if hinst['manage'] == 'ignore':
                continue

            cls = hinst['agent-class']
            srv = None  # The expected docker service name, if any

            mgmt, start_state = hinst['manage'].split('/')
            if mgmt == 'docker':
                cls = _clsname_tool(cls, '[d?]')
                srv = self.docker_service_prefix + iid

            # See if we already tracking this agent.
            instance = self.database.get(iid)

            if instance is not None:
                # Already tracking; just check for major config change.
                _cls = instance['agent_class']
                _mgmt = instance['management']
                if not same_base_class(_cls, cls) or _mgmt != mgmt:
                    session.add_message(
                        f'Managed agent "{iid}" changed agent_class '
                        f'({_cls} -> {cls}) or management '
                        f'({_mgmt} -> {mgmt}) and is being reset!')
                    # Bring down existing instance
                    self._terminate_instance(iid)
                    # Start a new one
                    instance = None

            # Do we have an unmatched docker entry for this?
            if instance is None and srv in self.database:
                # Re-register it under instance_id
                instance = self.database.pop(srv)
                self.database[iid] = instance
                instance.update({
                    'instance_id': iid,
                    'agent_class': _clsname_tool(cls, '[d]'),
                    'full_name': _full_name(cls, iid),
                })

            if instance is None:
                instance = hm_utils.ManagedInstance.init(
                    management=mgmt,
                    instance_id=iid,
                    agent_class=cls,
                    full_name=_full_name(cls, iid),
                )
                instance['target_state'] = start_state
                self.database[iid] = instance

        # Get agent class list from modern plugin system.
        agent_plugins = agent_cli.build_agent_list()

        # Assign plugins / scripts / whatever to any new instances.
        for iid, instance in self.database.items():
            if instance['agent_script'] is not None:
                continue
            if instance['management'] == 'host':
                cls = instance['agent_class']
                # Check for the agent class in the plugin system;
                # then check the (deprecated) agent script registry.
                if cls in agent_plugins:
                    session.add_message(f'Found plugin for "{cls}"')
                    instance['agent_script'] = '__plugin__'
                    instance['operable'] = True
                elif cls in site_config.agent_script_reg:
                    session.add_message(f'Found launcher script for "{cls}"')
                    instance['agent_script'] = site_config.agent_script_reg[cls]
                    instance['operable'] = True
                else:
                    session.add_message(f'No plugin (nor launcher script) '
                                        f'found for agent_class "{cls}"!')
            elif instance['management'] == 'docker':
                instance['agent_script'] = self.docker_service_prefix + iid

        # Read the compose files; query container states; updater stuff.
        yield self._update_docker_services(session)
        returnValue(warnings)

    def _launch_instance(self, instance):
        """Launch an Agent instance (whether 'host' or 'docker' managed) using
        hm_utils.

        For 'host' managed agents: hm_utils will use
        reactor.spawnProcess, and store the AgentProcessHelper (which
        inherits from twisted ProcessProtocol) in instance['prot'].
        The site_file and instance_id are passed on the command line;
        this means that any weird config overrides passed to this
        HostManager are not propagated.  One exception is working_dir,
        which is propagated in order that relative paths can make any
        sense.

        For 'docker' managed agents: hm_utils will try to start the
        right service container, and instance['prot'] will hold a
        DockerContainerHelper (which has some common interface with
        AgentProcessHelper).

        """
        if instance['management'] == 'docker':
            prot = instance['prot']
        else:
            iid = instance['instance_id']
            pyth = sys.executable
            script = instance['agent_script']
            if script == '__plugin__':
                cmd = [pyth, '-m', 'ocs.agent_cli']
            else:
                cmd = [pyth, script]
            cmd.extend([
                '--instance-id', iid,
                '--site-file', self.site_config_file,
                '--site-host', self.host_name,
                '--working-dir', self.working_dir])
            prot = hm_utils.AgentProcessHelper(iid, cmd)
        prot.up()
        instance['prot'] = prot

    def _terminate_instance(self, key):
        """
        Use the ProcessProtocol to request the Agent instance to exit.
        """
        prot = self.database[key]['prot']  # Get the ProcessProtocol.
        if prot is None:
            return True, 'Instance was not running.'
        if prot.killed:
            return True, 'Instance already has kill set.'
        # Note the .down call does not block -- the thing will be
        # stopped from a thread.
        prot.down()
        return True, 'Kill requested.'

    def _process_target_states(self, session, requests=[]):
        """This is a helper function for parsing target_state change
        requests; see the update Task.

        """
        # Special requests will target specific instance_id; make a map for that.
        addressable = {k: v for k, v in self.database.items()
                       if v['management'] != 'retired'}

        for key, state in requests:
            if state not in VALID_TARGETS:
                session.add_message('Ignoring request for "%s" -> invalid state "%s".' %
                                    (key, state))
                continue
            if key == 'all':
                for v in addressable.values():
                    v['target_state'] = state
            else:
                if key in addressable:
                    addressable[key]['target_state'] = state
                else:
                    session.add_message(f'Ignoring invalid target, {key}')

    @ocs_agent.param('requests', default=[])
    @ocs_agent.param('reload_config', default=True, type=bool)
    @inlineCallbacks
    def manager(self, session, params):
        """manager(requests=[], reload_config=True)

        **Process** - The "manager" Process maintains a list of child
        Agents for which it is responsible.  In response to requests
        from a client, the Process will launch or terminate child
        Agents.

        Args:

          requests (list): List of agent instance target state
            requests; e.g. [('instance1', 'down')].  See description
            in :meth:`update` Task.
          reload_config (bool): When starting up, discard any cached
            database of tracked agents and rescan the Site Config
            File.  This is mostly for debugging.

        Notes:

          If an Agent process exits unexpectedly, it will be
          relaunched within a few seconds.

          When this Process is started (or restarted), the list of
          tracked agents and their status is completely reset, and the
          Site Config File is read in.

          Once this process is running, the target states for managed
          Agents can be manipulated through the :meth:`update` task.

          Note that when a stop is requested on this Process, all
          managed Agents will be moved to the "down" state and an
          attempt will be made to terminate them before the Process
          exits.

          The session.data is a dict, and entry 'child_states'
          contains a list with the managed Agent statuses.  For
          example::

            {'child_states': [
              {'next_action': 'up',
               'target_state': 'up',
               'stability': 1.0,
               'agent_class': 'Lakeshore372Agent',
               'instance_id': 'thermo1'},
              {'next_action': 'down',
               'target_state': 'down',
               'stability': 1.0,
               'agent_class': 'ACUAgent',
               'instance_id': 'acu-1'},
              {'next_action': 'up',
               'target_state': 'up',
               'stability': 1.0,
               'agent_class': 'FakeDataAgent[d]',
               'instance_id': 'faker6'},
              ],
            }

          If you are looking for the "current state", it's called
          "next_action" here.

          The agent_class may include a suffix [d] or [d?], indicating
          that the agent is configured to run within a docker
          container.  (The question mark indicates that the
          HostManager cannot actually identify the docker-compose
          service associated with the agent description in the SCF.)

        """
        self.config_parse_status = {}
        session.data = {
            'child_states': [],
            'config_parse_status': self.config_parse_status,
        }

        self.running = True

        if params['reload_config']:
            self.database = {}
            yield self._reload_config(session)
        self._process_target_states(session, params['requests'])

        next_docker_update = time.time()

        any_jobs = False
        while self.running or any_jobs:

            if time.time() >= next_docker_update:
                yield self._update_docker_services(session)
                next_docker_update = time.time() + 2

            sleep_times = [1.]
            any_jobs = False

            for key, db in self.database.items():

                # If Process exit is requested, force all targets to down.
                if not self.running:
                    db['target_state'] = 'down'

                actions = hm_utils.resolve_child_state(db)

                for msg in actions['messages']:
                    session.add_message(msg)
                if actions['terminate']:
                    self._terminate_instance(key)
                if actions['launch']:
                    reactor.callFromThread(self._launch_instance, db)
                if actions['sleep']:
                    sleep_times.append(actions['sleep'])
                any_jobs = (any_jobs or (db['next_action'] != 'down'))

                # Criteria for stability:
                db['fail_times'], db['stability'] = hm_utils.stability_factor(
                    db['fail_times'])

            # Clean up retired items.
            self.database = {
                k: v for k, v in self.database.items()
                if v['management'] != 'retired' or v['next_action'] not in ['down', '?']}

            # Update session info.
            child_states = []
            for state in self.database.values():
                child_states.append({_k: state[_k] for _k in
                                     ['next_action',
                                      'target_state',
                                      'stability',
                                      'agent_class',
                                      'instance_id']})
            session.data['child_states'] = child_states

            yield dsleep(max(min(sleep_times), .001))
        return True, 'Exited.'

    @inlineCallbacks
    def _stop_manager(self, session, params):
        yield
        if session.status == 'done':
            return
        session.set_status('stopping')
        self.running = False
        return True, 'Stop initiated.'

    @ocs_agent.param('requests', default=[])
    @ocs_agent.param('reload_config', default=False, type=bool)
    @inlineCallbacks
    def update(self, session, params):
        """update(requests=[], reload_config=False)

        **Task** - Update the target state for any subset of the
        managed agent instances.  Optionally, trigger a full reload of
        the Site Config File first.

        Args:
          requests (list): Default is [].  Each entry must be a tuple
            of the form ``(instance_id, target_state)``.  The
            ``instance_id`` must be a string that matches an item in
            the current list of tracked agent instances, or be the
            string 'all', which will match all items being tracked.
            The ``target_state`` must be 'up' or 'down'.
          reload_config (bool): Default is False.  If True, the site
            config file and docker-compose files are reparsed in order
            to (re-)populate the database of child Agent instances.

        Examples:
          ::

            update(requests=[('thermo1', 'down')])
            update(requests=[('all', 'up')])
            update(reload_config=True)


        Notes:
          Starting and stopping agent instances is handled by the
          :meth:`manager` Process; if that Process is not running then
          no action is taken by this Task and it will exit with an
          error.

          The entries in the ``requests`` list are processed in order.
          For example, if the requests were [('all', 'up'), ('data1',
          'down')].  This would result in setting all known children
          to have target_state "up", except for "data1" which would be
          given target state of "down".

          If ``reload_config`` is True, the Site Config File will be
          reloaded (as described in :meth:`_reload_config`) before
          any of the requests are processed.

          Managed docker-compose.yaml files are reparsed, continously,
          by the manager process -- no specific action is taken with
          those in this Task.  Note that adding/changing the list of
          docker-compose.yaml files requires restarting the agent.

        """
        if not self.running:
            return False, 'Manager process is not running; params not updated.'
        if params['reload_config']:
            yield self._reload_config(session)
        self._process_target_states(session, params['requests'])
        return True, 'Update requested.'

    @inlineCallbacks
    def die(self, session, params):
        if not self.running:
            session.add_message('Manager process is not running.')
        else:
            session.add_message('Requesting exit of manager process.')
            ok, msg, mp_session = self.agent.stop('manager')
            ok, msg, mp_session = yield self.agent.wait('manager', timeout=10.)
            if ok == ocs.OK:
                session.add_message('... manager Process has exited.')
            else:
                session.add_message('... timed-out waiting for manager Process exit!')

        # Schedule program exit.
        reactor.callLater(1., reactor.stop)

        return True, 'This HostManager should terminate in about 1 second.'


def _clsname_tool(name, new_suffix=None):
    try:
        i = name.index('[')
    except ValueError:
        i = len(name)
    base, suffix = name[:i], name[i:]
    if new_suffix is None:
        return base, suffix
    return base + new_suffix


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default=None,
                        choices=['up', 'down'],
                        help="Force a single target state for all agents, "
                        "on start-up.")
    pgroup.add_argument('--docker-compose', default=None,
                        help="Comma-separated list of docker-compose files "
                        "to parse and manage.")
    pgroup.add_argument('--docker-service-prefix', default='ocs-',
                        help="Prefix, to be used in combination with "
                        "instance-id, for recognizing docker services "
                        "that correspond to entries in site config.")
    pgroup.add_argument('--docker-compose-bin', default=None,
                        help="Path to docker-compose binary.  This "
                        "will be interpreted as a path relative to "
                        "current working directory.  If not specified, "
                        "will try to use `which docker-compose`.")
    pgroup.add_argument('--quiet', action='store_true',
                        help="Suppress output to stdout/stderr.")
    return parser


def main(args=None):
    parser = make_parser()
    args = site_config.parse_args(agent_class='HostManager',
                                  parser=parser,
                                  args=args)

    if args.quiet:
        # For launch-to-background, disconnect stdio.
        null = os.open(os.devnull, os.O_RDWR)
        for stream in [sys.stdin, sys.stdout, sys.stderr]:
            os.dup2(null, stream.fileno())
        os.close(null)

    agent, runner = ocs_agent.init_site_agent(args)

    docker_composes = []
    if args.docker_compose:
        docker_composes = args.docker_compose.split(',')

    host_manager = HostManager(agent, docker_composes=docker_composes,
                               docker_service_prefix=args.docker_service_prefix)

    startup_params = {}
    if args.initial_state:
        startup_params = {'requests': [('all', args.initial_state)]}

    agent.register_process('manager',
                           host_manager.manager,
                           host_manager._stop_manager,
                           blocking=False,
                           startup=startup_params)
    agent.register_task('update', host_manager.update, blocking=False)
    agent.register_task('die', host_manager.die, blocking=False)

    reactor.addSystemEventTrigger('before', 'shutdown', agent._stop_all_running_sessions)
    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
