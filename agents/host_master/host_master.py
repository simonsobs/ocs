import ocs
from ocs import ocs_agent, site_config
from ocs.agent import host_manager as hm_utils

import time
import argparse

from twisted.internet import reactor, task, threads
from twisted.internet import protocol
from twisted.internet.defer import inlineCallbacks, Deferred, DeferredList, FirstError
from autobahn.twisted.util import sleep as dsleep

import threading
import socket
import os, sys

VALID_TARGETS = ['up', 'down']

class HostManager:
    """
    This Agent is used to start and stop OCS-relevant services on a
    particular host.  If the HostManager is launched automatically when
    a system boots, it can then be used to start up the rest of OCS on
    that host (either automatically or on request).
    """
    def __init__(self, agent, docker_composes=[]):
        self.agent = agent
        self.running = False
        self.database = {} # key is (class_name, instance_id)
        self.site_file = None
        self.docker_composes = docker_composes

    @inlineCallbacks
    def _get_instance_list(self):
        """Parse the site config and return a list of this host's Agent
        instances.

        Returns:
            List of (agent_class, instance_id) pairs.
        """
        # Load site config file.
        site, hc, _ = site_config.get_config(
            self.agent.site_args, '*host*')
        self.site_config_file = site.source_file
        self.host_name = hc.name
        self.working_dir = hc.working_dir

        # Add plugin paths and scan.
        for p in hc.agent_paths:
            if not p in sys.path:
                sys.path.append(p)
        site_config.scan_for_agents()
        
        # Construct the list; exclude HostManager class.
        keys = []
        for inst in hc.instances:
            class_name, instance_id = inst['agent-class'], inst['instance-id']
            manage = inst.get('manage', 'yes')
            if class_name == 'HostManager':
                manage = 'no'
            if manage == 'yes':
                keys.append((class_name, instance_id))

        # Add in services from specified docker-compose files.
        self.docker_services = {}
        for compose in self.docker_composes:
            services = yield hm_utils.parse_docker_state(compose)
            self.docker_services.update(services)
            for k in services.keys():
                keys.append(('docker', k))
        return keys

    @inlineCallbacks
    def _update_docker_states(self):
        """Scan the docker-compose files, again, and update the database
        information ('running' state, most importantly) for all
        services.

        """
        for compose in self.docker_composes:
            services = yield hm_utils.parse_docker_state(compose)
            for k, info in services.items():
                db = self.database[('docker', k)]
                if db['prot'] is None:
                    db['prot'] = hm_utils.DockerContainerHelper(info)
                db['prot'].update(info)

    def _launch_instance(self, key, script_file, instance_id):
        """
        Launch an Agent instance using reactor.spawnProcess.  The
        ProcessProtocol, which holds communication pathways to the
        process, will be registered in self.database.  The site_file
        and instance_id are passed on the command line; this means
        that any weird config overrides passed to this HostManager are
        not propagated.  One exception is working_dir, which is
        propagated in order that relative paths can make any sense.

        Because of the use of spawnProcess, this should be called in
        the reactor thread.

        """
        if key[0] == 'docker':
            prot = hm_utils.DockerContainerHelper(self.docker_services[instance_id])
        else:
            pyth = sys.executable
            cmd = [pyth, script_file,
                   '--instance-id', instance_id,
                   '--site-file', self.site_config_file,
                   '--site-host', self.host_name,
                   '--working-dir', self.working_dir]
            prot = hm_utils.AgentProcessHelper(instance_id, cmd)
        prot.up()
        self.database[key]['prot'] = prot

    def _terminate_instance(self, key):
        """
        Use the ProcessProtocol to request the Agent instance to exit.
        """
        prot = self.database[key]['prot'] # Get the ProcessProtocol.
        if prot is None:
            return True, 'Instance was not running.'
        if prot.killed:
            return True, 'Instance already has kill set.'
        prot.down()
        return True, 'Kill requested.'

    @inlineCallbacks
    def _update_target_states(self, session, params):
        """_update_target_states(params)

        Update the child Agent management parameters of the manager process.
        This function is used both for first-time init of the manager
        Process, but also for subsequent parameter updates while
        manager Process is running.

        The argument ``params`` is a dict with the following
        keys:

        - ``requests`` (list): Default is [].  Each entry must be a
          tuple of the form (instance_id, target_state).  The
          instance_id must be a string that matches an item in the
          current database, or be the string 'all', which will match
          all items in the current database.  The target_state must be
          one of 'up','down', or 'cycle'.  Requests in this list are
          processed from start to end, and subsequent entries overrule
          previous ones.

        - ``reload_site_config`` (bool): Default is True.  If True,
          the site config file is parsed in order to (re-)populate the
          database of child Agent instances.

        First, the site config file is parsed and used to update the
        internal database of child instances (unless
        ``reload_site_config`` has been set to False).  Any previously
        unknown child Agent is added to the internal tracking
        database, and assigned a target_state of "down".  Any
        previously known child Agent instance is not modified in the
        tracking database (unless a specific request is given, through
        ``requests``).  If any child Agent instances in the internal
        database appear to have been removed from the site config,
        then they are set to have target_state "down" and will be
        deleted from the database when that state is reached.

        State update requests in the ``requests`` list are processed
        in order.  For example, if the requests were [('all', 'up'),
        ('data1', 'down')].  This would result in setting all known
        children to have target_state "up", except for "data1" which
        would be given target state of "down".

        """
        if params is None:
            params = {}

        if params.get('reload_site_config', True):
            # Update the list of Agent instances.
            agent_keys = yield self._get_instance_list()
            session.add_message('Loaded %i agent instance configs.' %
                                len(agent_keys))
            downers = 0
            for k, item in self.database.items():
                # Any new keys?
                if k not in agent_keys:
                    item['retired'] = True
                    item['target_state'] = 'down'
                    downers += 1
            if downers > 0:
                session.add_message('Retiring %i instances that disappeared '
                                    'from config.' % downers)
            for k in agent_keys:
                if not k in self.database:
                    state = 'down'
                    if k[0] == 'docker':
                        agent_script = 'docker'
                        prot = hm_utils.DockerContainerHelper(self.docker_services[k[1]])
                        if prot.status[0] == None:
                            session.add_message(
                                'On startup, detected active container for %s' % k[1])
                            state = 'up'
                    else:
                        agent_script = site_config.agent_script_reg.get(k[0])
                        prot = None
                    self.database[k] = {
                        'next_action': state,
                        'target_state': state,
                        'class_name': k[0],
                        'instance_id': k[1],
                        'prot': prot,
                        'full_name': ('%s:%s' % tuple(k)),
                        'agent_script': agent_script,
                    }

        # Special requests will target specific instance_id; make a map for that.
        addressable = {}
        for k,v in self.database.items():
            if v.get('retired'):
                continue
            if k[1] in addressable:
                session.add_message('Internal state problem; multiple agents '
                                    'with instance_id=%s' % k[1])
                continue
            addressable[k[1]] = v

        requests = params.get('requests', [])
        for key, state in requests:
            if not state in VALID_TARGETS:
                session.add_message('Ignoring request for "%s" -> invalid state "%s".' %
                                    (key, state))
                continue
            if key == 'all':
                for v in addressable.values():
                    v['target_state'] = state
            else:
                if key in addressable:
                    addressable[key]['target_state'] = state

    @inlineCallbacks
    def manager(self, session, params):
        """manager(**kwargs)

        **Process** - The "manager" Process maintains a list of child Agents for
        which it is responsible.  In response to requests from a client, the
        Process will launch or terminate child Agents.

        If an Agent process exits unexpectedly, it will be relaunched
        within a few seconds.

        When the manager Process receives a stop request, it will terminate all
        child agents before moving to the 'done' state.

        Parameters:
            **kwargs: Passed directly to
                ``_update_target_states(params=kwargs)``; see
                :func:`HostManager._update_target_states`.

        """
        self.running = True
        session.set_status('running')
        self._update_target_states(session, params)

        session.data = {
            'child_states': [],
            'last_error': None,
        }

        dying_words = ['down', 'kill', 'wait_dead']  #allowed during shutdown

        next_docker_update = time.time()

        any_jobs = False
        while self.running or any_jobs:

            if time.time() >= next_docker_update:
                yield self._update_docker_states()
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
                        self._launch_instance, key, db['agent_script'],
                        db['instance_id'])
                if actions['sleep']:
                    sleep_times.append(actions['sleep'])
                any_jobs = (any_jobs or (db['next_action'] != 'down'))

            # Clean up retired items.
            self.database = {k:v for k,v in self.database.items()
                             if not v.get('retired') or v['next_action'] != 'down'}

            # Update session info.
            child_states = []
            for k,v in self.database.items():
                child_states.append({_k: v[_k] for _k in
                                     ['next_action' ,
                                      'target_state',
                                      'class_name',
                                      'instance_id']})
            session.data['child_states'] = child_states

            yield dsleep(max(min(sleep_times), .001))
        return True, 'Exited.'

    def _stop_manager(self, session, params):
        if session.status == 'done':
            return
        session.set_status('stopping')
        self.running = False
        return True, 'Stop initiated.'

    def update(self, session, params):
        """update(**kwargs)

        **Task** - Update the manager process' child Agent parameters.

        This Task will fail if the manager Process is not running.

        Parameters:
            **kwargs: Passed directly to
                ``_update_target_states(params=kwargs)``; see
                :func:`HostManager._update_target_states`.

        """
        if not self.running:
            return False, 'Manager process is not running; params not updated.'

        self._update_target_states(session, params)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default=None,
                        choices=['up', 'down'])
    pgroup.add_argument('--docker-compose', default=None,
                        help="Comma-separated list of docker-compose files to parse and manage.")
    pgroup.add_argument('--quiet', action='store_true')
    args = site_config.parse_args(agent_class='HostManager',
                                  parser=parser)

    if args.quiet:
        # For launch-to-background, disconnect stdio.
        null = os.open(os.devnull, os.O_RDWR)
        for stream in [sys.stdin, sys.stdout, sys.stderr]:
            os.dup2(null, stream.fileno())
        os.close(null)

    # To reduce "try again" noise, don't tell Registry about HostManager.
    args.registry_address = 'none'

    agent, runner = ocs_agent.init_site_agent(args)

    docker_composes = []
    if args.docker_compose:
        docker_composes = args.docker_compose.split(',')

    host_manager = HostManager(agent, docker_composes=docker_composes)

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
    runner.run(agent, auto_reconnect=True)

