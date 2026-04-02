import ocs
from ocs import ocs_agent, site_config, agent_cli
from ocs.agents.host_manager import drivers as hm_utils

import time
import argparse

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredList
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
        # The database maps instance_id (or docker service name, if
        # it's an unmanaged docker container) to a ManagedInstance.
        self.database = {}
        self.orphans = {}
        self.new_tags = {}
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

        # Gather managed items from site config.
        for inst in hc.instances:
            if 'instance-id' not in inst:
                warnings.append('Ignoring an entry with no instance-id!')
                continue
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
        orphans = {}
        new_tags = {}
        for compose in self.docker_composes:
            try:
                services, _orphans = yield hm_utils.parse_docker_state(compose)
                orphans.update(_orphans)
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
        for key, minst in self.database.items():
            if minst.management != 'docker':
                continue

            service_name = minst.agent_script
            service_data = docker_services.get(service_name)
            assigned_services.append(service_name)

            prot = minst.prot
            if prot is None:
                if service_data is not None:
                    # Create a prot entry with the service info.
                    minst.prot = hm_utils.DockerContainerHelper(service_data)
                    minst.operable = True
                    if minst.agent_class != NONAGENT_DOCKER:
                        minst.agent_class = _clsname_tool(minst.agent_class, '[d]')
                    # Update current_state to not trigger a "docker
                    # up" on a running container. Normally that would
                    # be a no-op, but not if image tag has changed.
                    if service_data['running']:
                        session.add_message(f'Docker-based instance {key} seems to be running.')
                        minst.next_action = 'up'

            else:
                if service_data is not None:
                    prot.update(service_data)
                else:
                    # service_data is missing, but there used to be a
                    # service there.  Close it out.
                    minst.prot = None
                    minst.operable = False
                    if minst.agent_class == NONAGENT_DOCKER:
                        session.add_message(f'Deleting non-agent service {key}')
                        retirees.append(key)
                    else:
                        session.add_message(f'Marking missing service for {key}')
                        minst.agent_class = _clsname_tool(minst.agent_class, '[d?]')

            restart_required = False
            if minst.prot is not None and service_data is not None \
               and service_data.get('running') \
               and (service_data.get('running_image') != service_data.get('image_id')):
                restart_required = True
            if service_data is not None and service_data.get('image_id') == 'unknown':
                new_tags[key] = service_data['image_tag']
            minst.restart_required = restart_required

        # If a non-agent [docker] service has disappeared, there's no
        # reason to show it in a list, and no persistent state /
        # operations to worry about.  So just delete it.
        for r in retirees:
            self.database.pop(r)

        # Create entries for any new un-matched docker services.
        unassigned_services = set(docker_services.keys()) \
            .difference(assigned_services)
        for srv in unassigned_services:
            session.add_message(f'Adding non-agent service "{srv}"')
            minst = hm_utils.ManagedInstance(
                management='docker',
                instance_id=srv,
                agent_class=NONAGENT_DOCKER,
                full_name=f'[docker]:{srv}',
                agent_script=srv,
                operable=True,
                passive_tracking=True,
                target_state='passive',
            )

            service_data = docker_services[srv]
            minst.prot = hm_utils.DockerContainerHelper(service_data)

            # If it's up, leave it up.
            if service_data['running']:
                minst.next_action = 'up'

            self.database[srv] = minst

        # Update the list of orphans ...
        orphans_gone = set(self.orphans.keys()).difference(orphans.keys())
        for k in orphans_gone:
            del self.orphans[k]
        self.orphans.update(orphans)

        # And new tags that need a docker pull ...
        self.new_tags = new_tags

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
            minst = self.database.get(db_key, None)
            if minst is None:
                return
            minst.management = 'retired'
            minst.at = time.time()
            minst.target_state = 'down'

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
        for iid, minst in self.database.items():
            if minst.agent_class != NONAGENT_DOCKER and (
                    iid not in agent_dict or agent_dict[iid].get('manage') == 'ignore'):
                session.add_message(
                    f'Retiring {minst.full_name}, which has disappeared from '
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
            minst = self.database.get(iid)

            if minst is not None:
                # Already tracking; just check for major config change.
                _cls = minst.agent_class
                _mgmt = minst.management
                if not same_base_class(_cls, cls) or _mgmt != mgmt:
                    session.add_message(
                        f'Managed agent "{iid}" changed agent_class '
                        f'({_cls} -> {cls}) or management '
                        f'({_mgmt} -> {mgmt}) and is being reset!')
                    # Bring down existing instance
                    self._terminate_instance(iid)
                    # Start a new one
                    minst = None

            # Do we have an unmatched docker entry for this?
            if minst is None and srv in self.database:
                session.add_message(
                    f'Unmanaged docker service {srv} will now be managed as '
                    f'instance_id={iid}.')
                # Re-register it under instance_id
                minst = self.database.pop(srv)
                minst.instance_id = iid
                minst.agent_class = _clsname_tool(cls, '[d]')
                minst.full_name = _full_name(cls, iid)
                minst.passive_tracking = False
                if minst.target_state == 'passive':
                    minst.target_state = \
                        minst.next_action if minst.next_action in ['up', 'down'] else 'down'
                self.database[iid] = minst

            if minst is None:
                minst = hm_utils.ManagedInstance(
                    management=mgmt,
                    instance_id=iid,
                    agent_class=cls,
                    full_name=_full_name(cls, iid),
                    target_state=start_state,
                )
                self.database[iid] = minst

        # Get agent class list from modern plugin system.
        agent_plugins = agent_cli.build_agent_list()

        # Assign plugins / scripts / whatever to any new instances.
        for iid, minst in self.database.items():
            if minst.agent_script is not None:
                continue
            if minst.management == 'host':
                cls = minst.agent_class
                # Check for the agent class in the plugin system
                if cls in agent_plugins:
                    session.add_message(f'Found plugin for "{cls}"')
                    minst.agent_script = '__plugin__'
                    minst.operable = True
                else:
                    session.add_message('No plugin '
                                        f'found for agent_class "{cls}"!')
            elif minst.management == 'docker':
                minst.agent_script = self.docker_service_prefix + iid

        # Read the compose files; query container states; updater stuff.
        yield self._update_docker_services(session)
        returnValue(warnings)

    def _launch_instance(self, minst):
        """Launch an Agent instance (whether 'host' or 'docker' managed) using
        hm_utils.

        For 'host' managed agents: hm_utils will use
        reactor.spawnProcess, and store the AgentProcessHelper (which
        inherits from twisted ProcessProtocol) in minst.prot.
        The site_file and instance_id are passed on the command line;
        this means that any weird config overrides passed to this
        HostManager are not propagated.  One exception is working_dir,
        which is propagated in order that relative paths can make any
        sense.

        For 'docker' managed agents: hm_utils will try to start the
        right service container, and minst.prot will hold a
        DockerContainerHelper (which has some common interface with
        AgentProcessHelper).

        """
        if minst.management == 'docker':
            prot = minst.prot
        else:
            iid = minst.instance_id
            pyth = sys.executable
            cmd = [pyth, '-m', 'ocs.agent_cli',
                   '--instance-id', iid,
                   '--site-file', self.site_config_file,
                   '--site-host', self.host_name,
                   '--working-dir', self.working_dir]
            prot = hm_utils.AgentProcessHelper(iid, cmd)
        prot.up()
        minst.prot = prot

    def _terminate_instance(self, key):
        """
        Use the ProcessProtocol to request the Agent instance to exit.
        """
        prot = self.database[key].prot  # Get the ProcessProtocol.
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
        addressable = {k: minst for k, minst in self.database.items()
                       if minst.management != 'retired'}
        for key, state in requests:
            if state not in VALID_TARGETS:
                session.add_message('Ignoring request for "%s" -> invalid state "%s".' %
                                    (key, state))
                continue
            if key == 'all':
                for minst in addressable.values():
                    minst.target_state = state
            else:
                if key in addressable:
                    addressable[key].target_state = state
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

          The session.data is a dict, with entries:
          - 'child_states'
          - 'config_parse_status' - indicates how recently the various
            input files havebeen parsed.
          - 'orphans' - lists any orphaned (in the sense of docker
            compose) containers.
          - 'new_tags' - dict mapping instance_id to new docker image
            tag, if that tag is not known to docker system. Only
            populated for tracked instances where the tag is not
            known.

          The 'child_states' entry is a list of managed Agent status;
          for example::

            [
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
              ]

          If you are looking for the "current state", it's called
          "next_action" here.

          The agent_class may include a suffix [d] or [d?], indicating
          that the agent is configured to run within a docker
          container.  (The question mark indicates that the
          HostManager cannot actually identify the docker-compose
          service associated with the agent description in the SCF.)

          The 'config_parse_status' is a dict where the key is a
          docker compose filename, or "[SCF]" for the site config
          file, and the value is a tuple (success, timestamp,
          message).

          The 'orphans' entry is as a dict mapping docker container ID
          to some information about the container.  E.g.::

            {
              "30027f37e0ef4b...": {
                "compose_file": "/home/ocs/config/docker-compose.yml",
                "service": "ocs-faker3",
                "container_id": "30027f37e0ef4b...",
                "running": true,
                "exit_code": 0,
                "container_found": true,
                "running_image": "sha256:7eaa6d6f6..."
              }
            }

        The 'new_tags' entry looks like this::

          {
            "faker1": "simonsobs/ocs:v0.11.3",
            "faker2": "simonsobs/ocs:v0.11.3"
          }

        """
        self.config_parse_status = {}
        session.data = {
            'child_states': [],
            'config_parse_status': self.config_parse_status,
            'orphans': self.orphans,
            'new_tags': self.new_tags,
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

            for key, minst in self.database.items():

                # If Process exit is requested, force all targets to down.
                if not self.running and not minst.passive_tracking:
                    minst.target_state = 'down'

                actions = hm_utils.resolve_child_state(minst)

                for msg in actions['messages']:
                    session.add_message(msg)
                if actions['terminate']:
                    self._terminate_instance(key)
                if actions['launch']:
                    reactor.callFromThread(self._launch_instance, minst)
                if actions['sleep']:
                    sleep_times.append(actions['sleep'])

                if minst.passive_tracking:
                    this_job = minst.next_action != 'passive'
                else:
                    this_job = minst.next_action != 'down'
                any_jobs = (any_jobs or this_job)

                # Criteria for stability:
                minst.fail_times, minst.stability = hm_utils.stability_factor(
                    minst.fail_times)

            # Clean up retired items.
            self.database = {
                k: minst for k, minst in self.database.items()
                if minst.management != 'retired' or minst.next_action not in ['down', '?']}

            # Update session info.
            child_states = []
            for minst in self.database.values():
                child_states.append({_k: getattr(minst, _k) for _k in
                                     ['next_action',
                                      'target_state',
                                      'stability',
                                      'agent_class',
                                      'instance_id',
                                      'operable',
                                      'restart_required',
                                      ]})
            session.data['child_states'] = child_states
            session.data['new_tags'] = self.new_tags

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
    def remove_orphans(self, session, params):
        """remove_orphans(stop_time=10.)

        **Task** - Use docker stop and docker rm to remove orphaned
        containers associated with managed docker compose files.

        This does not really do any error checking.
        """
        containers = list(self.orphans.values())
        session.add_message(f'Attempting stop and remove of {len(containers)} containers.')

        defs = []
        for cont in containers:
            print(f'Stopping {cont["container_id"][:16]} ...')
            d = hm_utils._run_docker(['stop', cont['container_id']])
            defs.append(d)

        yield DeferredList(defs)

        defs = []
        for cont in containers:
            print(f'Removing {cont["container_id"][:16]} ...')
            d = hm_utils._run_docker(['rm', cont['container_id']])
            defs.append(d)

        yield DeferredList(defs)

        return True, 'Done.'

    @inlineCallbacks
    def docker_pull(self, session, params):
        """docker_pull()

        **Task** - Use docker compose to pull any (new) images for the
        managed docker compose files.

        """
        for compose in self.docker_composes:
            session.add_message(f'Running pull for {compose} ...')
            yield hm_utils._run_docker(['compose', '-f', compose, 'pull'])

        return True, 'Done.'

    @inlineCallbacks
    @ocs_agent.param('disown_dockers', default=False, type=bool)
    def die(self, session, params):
        """die(disown_dockers=False)

        **Task** - trigger a shutdown of the manage process and then
        stop the reactor, causing the HostManager to exit.

        Args:
          disown_dockers (bool): If True, then all tracked docker
            services will be put in "passive tracking" mode, meaning
            that they will not be stopped and removed during this
            shutdown process.  This can be used to restart HostManager
            without needing to also restart all (docker-based) agents
            on the system.

        """
        if params['disown_dockers']:
            for minst in self.database.values():
                if minst.management == 'docker':
                    minst.passive_tracking = True
                    if minst.target_state in ['up', 'down']:
                        minst.target_state = 'passive'

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
    agent.register_task('remove_orphans', host_manager.remove_orphans, blocking=False)
    agent.register_task('docker_pull', host_manager.docker_pull, blocking=False)
    agent.register_task('die', host_manager.die, blocking=False)

    reactor.addSystemEventTrigger('before', 'shutdown', agent._stop_all_running_sessions)
    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
