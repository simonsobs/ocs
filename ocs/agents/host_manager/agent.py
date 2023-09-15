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


class HostManager:
    """
    This Agent is used to start and stop OCS-relevant services on a
    particular host.  If the HostManager is launched automatically when
    a system boots, it can then be used to start up the rest of OCS on
    that host (either automatically or on request).
    """

    def __init__(self, agent, docker_composes=[], docker_compose_bin=None,
                 docker_service_prefix='ocs-'):
        self.agent = agent
        self.running = False
        self.database = {}  # key is instance_id (or docker service name).
        self.docker_services = {}  # key is service name.
        self.docker_composes = docker_composes
        self.docker_compose_bin = docker_compose_bin
        self.docker_service_prefix = docker_service_prefix

    @inlineCallbacks
    def _get_local_instances(self):
        """Parse the site config and return a list of this host's Agent
        instances.

        Returns:
          agent_dict (dict): Maps instance-id to a dict describing the
            agent config.  The config is as contained in
            HostConfig.instances but where 'instance-id', 'agent-class'
            or 'agent-exe', and 'manage' are all guaranteed populated
            (and manage is one of ['yes', 'no', 'docker']).
          warnings: A list of strings, each of which corresponds to
            some problem found in the config.

        """
        # Load site config file.
        site, hc, _ = site_config.get_config(
            self.agent.site_args, '*host*')
        self.site_config_file = site.source_file
        self.host_name = hc.name
        self.working_dir = hc.working_dir
        self.wamp_url = site.hub.data['wamp_server']
        self.wamp_realm = site.hub.data['wamp_realm']
        self.address_root = site.hub.data['address_root']
        self.log_dir = hc.log_dir

        # Scan for agent scripts in (deprecated) script registry
        for p in hc.agent_paths:
            if p not in sys.path:
                sys.path.append(p)
        site_config.scan_for_agents()

        # Gather managed items from site config.
        warnings = []
        instances = {}
        for inst in hc.instances:
            if inst['instance-id'] in instances:
                warnings.append(
                    f'Configuration problem, instance-id={inst["instance-id"]} '
                    f'has multiple entries.  Ignoring repeats.')
                continue
            # Make sure 'manage' is set, and valid.
            default_manage = 'no' \
                if 'agent-class' in inst and inst['agent-class'] == 'HostManager' else 'yes'
            inst['manage'] = inst.get('manage', default_manage)
            if inst['manage'] not in ['yes', 'no', 'docker']:
                warnings.append(
                    f'Configuration problem, invalid manage={inst["manage"]} '
                    f'for instance_id={inst["instance-id"]}.')
                continue
            instances[inst['instance-id']] = inst
            # Make sure either 'agent-class' or 'agent-exe' is set, but not both
            if 'agent-class' not in inst and 'agent-exe' not in inst:
                warnings.append(
                    f'Configuration problem, neither agent-class nor agent-exe is set'
                    f'for instance_id={inst["instance-id"]}.')
                continue
            if inst.get('agent-class') is not None and inst.get('agent-exe') is not None:
                warnings.append(
                    f'Configuration problem, both agent-class and agent-exe are set'
                    f'for instance_id={inst["instance-id"]}.')
                continue
        returnValue((instances, warnings))
        yield

    @inlineCallbacks
    def _update_docker_services(self):
        """Parse the docker-compose.yaml files and update the internal cache
        of docker service information.

        Returns:
          dead (dict): a dict of service entries that were removed
            from self.docker_services because they are nolonger
            configured in any compose file.

        """
        # Read services from all docker-compose files.
        docker_services = {}
        for compose in self.docker_composes:
            services = yield hm_utils.parse_docker_state(
                compose, docker_compose_bin=self.docker_compose_bin)
            docker_services.update(services)

        # Mark containers that have disappeared.
        dead = {}
        for k in self.docker_services:
            if k not in docker_services:
                dead[k] = self.docker_services.pop(k)

        # Everything else is good.
        self.docker_services.update(docker_services)
        returnValue(dead)

    @inlineCallbacks
    def _reload_config(self, session):
        """
        Notes:
          First, the site config file is parsed and used to update the
          internal database of child instances.  Any previously
          unknown child Agent is added to the internal tracking
          database, and assigned a target_state of "down".  Any
          previously known child Agent instance is not modified in the
          tracking database (unless a specific request is given,
          through ``requests``).  If any child Agent instances in the
          internal database appear to have been removed from the site
          config, then they are set to have target_state "down" and
          will be deleted from the database when that state is
          reached.
        """
        # Parse the site config and compose files.
        agent_dict, warnings = yield self._get_local_instances()
        for w in warnings:
            session.add_message(w)
        yield self._update_docker_services()

        # Get agent class list from modern plugin system.
        agent_plugins = agent_cli.build_agent_list()

        def retire(db_key):
            instance = self.database.get(db_key, None)
            if instance is None:
                return
            instance['management'] = 'retired'
            instance['at'] = time.time()
            instance['target_state'] = 'down'

        # First identify items that we were managing that have
        # disappeared from the configs.
        for iid, instance in self.database.items():
            if (instance['management'] == 'host'
                and iid not in agent_dict) or \
               (instance['management'] == 'docker'
                    and instance['agent_script'] not in self.docker_services):
                # Sheesh
                session.add_message(
                    f'Retiring {instance["full_name"]}, which has disappeared from '
                    f'configuration file(s) or have manage:no.')
                retire(iid)

        # We have three kinds of managed things:
        # - agents managed on the host system (iid only)
        # - agents managed through docker (iid & srv)
        # - non-agents managed through docker (srv only)
        #
        # Make a list of items we need to manage, including all three
        # kinds of thing.  Store tuples:
        #   (db_key, instance_id, service_name, agent_class, management)
        new_managed = []
        docker_nonagents = list(self.docker_services.keys())

        for iid, hinst in agent_dict.items():
            record = dict(hinst)
            record['srv'] = self.docker_service_prefix + iid
            record['mgmt'] = 'host'
            if record['srv'] in docker_nonagents:
                docker_nonagents.remove(record['srv'])
                record['agent-class'] += '[d]'
                record['mgmt'] = 'docker'
                if hinst['manage'] != 'docker':
                    session.add_message(
                        f'The agent config for instance-id='
                        f'{iid} was matched to docker service '
                        f'{record["srv"]}, but config does not specify '
                        f'manage:docker! Dropping both.')
                    retire(iid)
                    continue
            else:
                record['srv'] = None
                if hinst['manage'] == 'no':
                    continue
                if hinst['manage'] == 'docker':
                    session.add_message(
                        f'No docker config found for instance-id='
                        f'{iid}, though manage:docker specified '
                        f'in config.  Dropping.')
                    retire(iid)
                    continue
            record['db_key'] = iid
            new_managed.append(record)

        for srv in docker_nonagents:
            new_managed.append({'db_key': srv, 'instance-id': srv, 'srv': srv,
                                'agent-class': '[docker]', 'mgmt': 'docker'})

        # Compare new managed items to stuff already in our database.
        for record in new_managed:
            db_key = record['db_key']
            instance = self.database.get(db_key, None)
            if instance is not None and \
               instance['management'] == 'retired':
                instance = None
            if instance is not None:
                # So instance is some kind of actively managed container.
                if (instance['agent_class'] != record.get('agent-class')
                        or instance['agent_exe'] != record.get('agent-exe')
                        or instance['management'] != record.get('mgmt')):
                    session.add_message(
                        f'Managed agent "{db_key}" changed agent_class '
                        f'({instance["agent_class"]} -> {record.get("agent-class")}) or agent_exe '
                        f'({instance["agent_exe"]} -> {record.get("agent-exe")}) or management '
                        f'({instance["management"]} -> {record.get("mgmt")}) and is being '
                        f'reset!')
                    instance = None
            if instance is None:
                if record.get("agent-class") is not None:
                    full_name = (f'{record["agent-class"]}:{record["db_key"]}')
                else:
                    full_name = (f'{record["agent-exe"]}:{record["db_key"]}')
                instance = hm_utils.ManagedInstance.init(
                    management=record.get("mgmt"),
                    instance_id=record.get("instance-id"),
                    agent_class=record.get("agent-class"),
                    agent_exe=record.get("agent-exe"),
                    full_name=full_name,
                    agent_arguments=record.get("arguments"),
                    write_logs=record.get("write-logs", True)
                )
                if record['mgmt'] == 'docker':
                    instance['agent_script'] = record['srv']
                    instance['prot'] = self._get_docker_helper(instance)
                    if instance['prot'].status[0] is None:
                        session.add_message(
                            'On startup, detected active container for %s' % iid)
                        # Mark current state as up... by the end
                        # of this function target_state will be up
                        # or down and that will determine if
                        # container is left up or stopped.
                        instance['next_action'] = 'up'
                else:
                    # Check for the agent class in the plugin system;
                    # then check the (deprecated) agent script registry.
                    if record.get("agent-exe") is not None:
                        pass
                    elif record.get("agent-class") in agent_plugins:
                        session.add_message(f'Found plugin for "{record.get("agent-class")}"')
                        instance['agent_script'] = '__plugin__'
                    elif record.get("agent-class") in site_config.agent_script_reg:
                        session.add_message(f'Found launcher script for "{record.get("agent-class")}"')
                        instance['agent_script'] = site_config.agent_script_reg[record.get("agent-class")]
                    else:
                        session.add_message(f'No plugin (nor launcher script) '
                                            f'found for agent_class "{record.get("agent-class")}"!')
                session.add_message(f'Tracking {instance["full_name"]}')
                self.database[db_key] = instance
        yield warnings

    @inlineCallbacks
    def _check_docker_states(self):
        """Scan the docker-compose files, again, and update the database
        information ('running' state, most importantly) for all
        services.

        It is the policy of this function to ignore things that are
        odd rather than deal with them somehow.

        """
        # Dict of database entries, indexed by docker service name.
        docker_managed = {info['agent_script']: info
                          for info in self.database.values()
                          if info['management'] == 'docker'}
        for compose in self.docker_composes:
            services = yield hm_utils.parse_docker_state(
                compose, docker_compose_bin=self.docker_compose_bin)
            for k, info in services.items():
                db = docker_managed.get(k)
                if db is not None:
                    if db['prot'] is None:
                        db['prot'] = self._get_docker_helper(db)
                    db['prot'].update(info)

    def _get_docker_helper(self, instance):
        service_name = instance['agent_script']
        return hm_utils.DockerContainerHelper(
            self.docker_services[service_name],
            docker_compose_bin=self.docker_compose_bin)

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
            prot = self._get_docker_helper(instance)
        else:
            iid = instance['instance_id']
            if instance.get('agent_script') is not None:
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
            elif instance.get('agent_exe') is not None:
                cmd = [instance['agent_exe'], '--address', self.address_root + '.' + iid,
                       '--wamp-url', self.wamp_url, '--wamp-realm', self.wamp_realm]
                if "agent_arguments" in instance:
                    cmd.extend(instance["agent_arguments"])
            if instance['write_logs'] and self.log_dir is not None:
                log_file_path = self.log_dir + '/' + self.address_root + '.' + iid + ".log"
            else:
                log_file_path = None
            prot = hm_utils.AgentProcessHelper(iid, cmd, log_file=log_file_path)
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
        """Update the child Agent target states.  The manager Process will
        then try to maintain those states.  This function is used both
        for first-time init of the manager Process, but also for
        setting new target states while the manager Process is
        running.

        Arguments:
          session: The operation session object (for logging).
          requests (list): Default is [].  Each entry must be a tuple
            of the form (instance_id, target_state).  The instance_id
            must be a string that matches an item in the current
            database, or be the string 'all', which will match all
            items in the current database.  The target_state must be
            'up' or 'down'.
          reload_config (bool): Default is True.  If True, the site
            config file and docker-compose files are reparsed in order
            to (re-)populate the database of child Agent instances.

        Examples:

          ::

            _process_target_states(session, requests=[('thermo1', 'down')])
            _process_target_states(session, requests=[('all', 'up')])

        Notes:
          State update requests in the ``requests`` list are processed
          in order.  For example, if the requests were [('all', 'up'),
          ('data1', 'down')].  This would result in setting all known
          children to have target_state "up", except for "data1" which
          would be given target state of "down".

        """
        # Special requests will target specific instance_id; make a map for that.
        addressable = {}
        for k, v in self.database.items():
            if v['management'] == 'retired':
                continue
            if k in addressable:
                session.add_message('Internal state problem; multiple agents '
                                    'with instance_id=%s' % k[1])
                continue
            addressable[k] = v

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

    @ocs_agent.param('requests', default=[])
    @ocs_agent.param('reload_config', default=True, type=bool)
    @inlineCallbacks
    def manager(self, session, params):
        """manager(requests=[], reload_config=True)

        **Process** - The "manager" Process maintains a list of child
        Agents for which it is responsible.  In response to requests
        from a client, the Process will launch or terminate child
        Agents.

        Notes:

          If an Agent process exits unexpectedly, it will be
          relaunched within a few seconds.

          Prior to starting the management loop, this function
          (re-)parses the site config and docker compose files (unless
          ``reload_config`` is False).  It passes ``requests`` to the
          ``_update_target_states`` function; please see that
          docstring for formatting.

          Once this process is running, the target states for managed
          Agents can be manipulated through the ``update`` task.

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
               'agent_class': 'FakeDataAgent',
               'instance_id': 'faker6'},
              ],
            }

          If you are looking for the "current state", it's called
          "next_action" here.

        """
        self.running = True
        session.set_status('running')

        if params['reload_config']:
            yield self._reload_config(session)
        self._process_target_states(session, params['requests'])

        session.data = {
            'child_states': [],
        }

        next_docker_update = time.time()

        any_jobs = False
        while self.running or any_jobs:

            if time.time() >= next_docker_update:
                yield self._check_docker_states()
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
                    reactor.callFromThread(
                        self._launch_instance, db)
                if actions['sleep']:
                    sleep_times.append(actions['sleep'])
                any_jobs = (any_jobs or (db['next_action'] != 'down'))

                # Criteria for stability:
                db['fail_times'], db['stability'] = hm_utils.stability_factor(
                    db['fail_times'])

            # Clean up retired items.
            self.database = {k: v for k, v in self.database.items()
                             if v['management'] != 'retired' or v['next_action'] != 'down'}

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

        **Task** - Update the manager process' child Agent parameters.

        This Task will fail if the manager Process is not running.

        If ``reload_config`` is True, the management agent
        configuration will be reloaded by ``_reload_config``.  Then
        the ``requests`` are passed to ``_process_target_states``.
        See those docstrings for more info.

        """
        if not self.running:
            return False, 'Manager process is not running; params not updated.'
        session.set_status('running')
        if params['reload_config']:
            yield self._reload_config(session)
        self._process_target_states(session, params['requests'])
        return True, 'Update requested.'

    @inlineCallbacks
    def die(self, session, params):
        session.set_status('running')
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


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default=None,
                        choices=['up', 'down'],
                        help="Sets the target state for managed agents, "
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
        docker_compose_bin = args.docker_compose_bin
        if args.docker_compose_bin is not None:
            docker_compose_bin = os.path.join(os.getcwd(), docker_compose_bin)

    host_manager = HostManager(agent, docker_composes=docker_composes,
                               docker_compose_bin=args.docker_compose_bin,
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
