import ocs
from ocs import ocs_agent, site_config
import time

from twisted.internet import reactor, task, threads
from twisted.internet import protocol
from twisted.internet.defer import inlineCallbacks, Deferred, DeferredList, FirstError
from autobahn.twisted.util import sleep as dsleep

import threading
import socket
import os, sys

VALID_TARGETS = ['up', 'down']

class HostMaster:
    """
    This Agent is used to start and stop OCS-relevant services on a
    particular host.  If the HostMaster is launched automatically when
    a system boots, it can then be used to start up the rest of OCS on
    that host (either automatically or on request).
    """
    def __init__(self, agent):
        self.agent = agent
        self.running = False
        self.database = {} # key is (class_name, instance_id)
        self.site_file = None

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
        
        # Construct the list; exclude HostMaster class.
        keys = []
        for inst in hc.instances:
            class_name, instance_id = inst['agent-class'], inst['instance-id']
            if class_name == 'HostMaster':
                continue
            keys.append((class_name, instance_id))
        return keys

    def _launch_instance(self, key, script_file, instance_id):
        """
        Launch an Agent instance using reactor.spawnProcess.  The
        ProcessProtocol, which holds communication pathways to the
        process, will be registered in self.database.  The site_file
        and instance_id are passed on the command line; this means
        that any weird config overrides passed to this HostMaster are
        not propagated.  One exception is working_dir, which is
        propagated in order that relative paths can make any sense.

        Because of the use of spawnProcess, this should be called in
        the reactor thread.

        """
        pyth = sys.executable
        cmd = [pyth, script_file,
               '--instance-id', instance_id,
               '--site-file', self.site_config_file,
               '--site-host', self.host_name,  # why does host prop?
               '--working-dir', self.working_dir]
        prot = AgentProcessProtocol()
        prot.instance_id = instance_id # probably only used for logging.
        reactor.spawnProcess(prot, cmd[0], cmd[:], env=os.environ)
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
        prot.killed = True
        # race condition, but it could be worse.
        if prot.status[0] is None:
            reactor.callFromThread(prot.transport.signalProcess, 'INT')
        return True, 'Kill requested.'

    def _update_target_states(self, session, params):
        """Update the child Agent management parameters of the master process.
        This function is used both for first-time init of the master
        Process, but also for subsequent parameter updates while
        master Process is running.

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
            agent_keys = self._get_instance_list()
            session.add_message('Loaded %i agent instance configs.' %
                                len(agent_keys))
            downers = 0
            for k,item in self.database.items():
                if not k in agent_keys:
                    item['retired'] = True
                    item['target_state']: 'down'
                    downers += 1
            if downers > 0:
                session.add_message('Retiring %i instances that disappeared '
                                    'from config.' % downers)
            for k in agent_keys:
                if not k in self.database:
                    self.database[k] = {
                        'next_action': 'down',
                        'target_state': 'down',
                        'class_name': k[0],
                        'instance_id': k[1],
                        'prot': None,
                        'full_name': ('%s:%s' % tuple(k)),
                        'agent_script': site_config.agent_script_reg.get(k[0]),
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
    def master_process(self, session, params=None):
        """The "master" Process maintains a list of child Agents for which it
        is responsible.  In response to requests from a client, the
        Proces will launch or terminate child Agents.

        If an Agent process exits unexpectedly, it will be relaunched
        within a few seconds.

        When the master_process receives a Process stop request, it
        will terminate all child agents before moving to the 'done'
        state.

        The ``params`` dictionary is passed directly to
        _update_target_states(); see that docstream.

        """
        self.running = True
        session.set_status('running')
        self._update_target_states(session, params)

        session.data = {}

        dying_words = ['down', 'kill', 'wait_dead']  #allowed during shutdown

        any_jobs = False
        while self.running or any_jobs:

            sleep_time = 1.
            any_jobs = False

            for key, db in self.database.items():
                # State machine.
                prot = db['prot']

                # If Process exit is requested, force all targets to down.
                if not self.running:
                    db['target_state'] = 'down'
                    
                # The uninterruptible transition state(s) are most easily handled
                # in the same way regardless of target state.

                # Transitional: wait_start, which bridges from start -> up.
                if db['next_action'] == 'wait_start':
                    if prot is not None:
                        session.add_message('Launched {full_name}'.format(**db))
                        db['next_action'] = 'up'
                    else:
                        if time.time() >= db['at']:
                            session.add_message('Launch not detected for '
                                                '{full_name}!  Will retry.'.format(**db))
                            db['next_action'] = 'start_at'
                            db['at'] = time.time() + 5.

                # Transitional: wait_dead, which bridges from kill -> idle.
                elif db['next_action'] == 'wait_dead':
                    if prot is None:
                        stat, t = 0, None
                    else:
                        stat, t = prot.status
                    if stat is not None:
                        db['next_action'] = 'down'
                    elif time.time() >= db['at']:
                        if stat is None:
                            session.add_message('Agent instance {full_name} '
                                                'refused to die.'.format(**db))
                            db['next_action'] = 'down'
                    else:
                        sleep_time = min(sleep_time, db['at'] - time.time())

                # State handling when target is to be 'up'.
                elif db['target_state'] == 'up':
                    if db['next_action'] == 'start_at':
                        if time.time() >= db['at']:
                            db['next_action'] = 'start'
                        else:
                            sleep_time = min(sleep_time, db['at'] - time.time())
                    elif db['next_action'] == 'start':
                        # Launch.
                        if db['agent_script'] is None:
                            session.add_message('No Agent script registered for '
                                                'class: {class_name}'.format(**db))
                            db['next_action'] = 'down'
                        else:
                            session.add_message(
                                'Requested launch for {full_name}'.format(**db))
                            db['prot'] = None
                            reactor.callFromThread(
                                self._launch_instance, key, db['agent_script'],
                                db['instance_id'])
                            db['next_action'] = 'wait_start'
                            db['at'] = time.time() + 1.
                    elif db['next_action'] == 'up':
                        stat, t = prot.status
                        if stat is not None:
                            # Right here would be a great place to check
                            # the stat return code, and include a traceback from stderr 
                            session.add_message('Detected exit of {full_name} '
                                                'with code {stat}.'.format(stat=stat, **db))
                            db['next_action'] = 'start_at'
                            db['at'] = time.time() + 3
                    else:  # 'down'
                        db['next_action'] = 'start'

                # State handling when target is to be 'down'.
                elif db['target_state'] == 'down':
                    if db['next_action'] == 'down':
                        pass
                    elif db['next_action'] == 'up':
                        session.add_message('Requesting termination of '
                                            '{full_name}'.format(**db))
                        self._terminate_instance(key)
                        db['next_action'] = 'wait_dead'
                        db['at'] = time.time() + 5
                    else: # 'start_at', 'start'
                        session.add_message('Modifying state of {full_name} from '
                                            '{next_action} to idle'.format(**db))
                        db['next_action'] = 'down'

                # Should not get here.
                else:
                    session.add_message(
                        'State machine failure: state={next_action}, target_state'
                        '={target_state}'.format(**db))

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
            session.data = child_states

            yield dsleep(max(sleep_time, .001))
        return True, 'Exited.'

    def master_process_stop(self, session, params=None):
        if session.status == 'done':
            return
        session.set_status('stopping')
        self.running = False
        return True, 'Stop initiated.'

    def update_task(self, session, params=None):
        """Update the master process' child Agent parameters.

        This Task will fail if the master Process is not running.

        The ``params`` dictionary is passed directly to
        _update_target_states(); see that docstream.

        """
        if not self.running:
            return False, 'Master process is not running; params not updated.'

        self._update_target_states(session, params)
        return True, 'Update requested.'

    @inlineCallbacks
    def die(self, session, params=None):
        session.set_status('running')
        if not self.running:
            session.add_message('Master process is not running.')
        else:
            session.add_message('Requesting exit of master process.')
            ok, msg, mp_session = self.agent.stop('master')
            ok, msg, mp_session = yield self.agent.wait('master', timeout=10.)
            if ok == ocs.OK:
                session.add_message('... master Process has exited.')
            else:
                session.add_message('... timed-out waiting for master Process exit!')
        # Die.
        self.agent.leave()
        return True, 'Quitting.'


class AgentProcessProtocol(protocol.ProcessProtocol):
    # See https://twistedmatrix.com/documents/current/core/howto/process.html
    #
    # These notes, and the useless prototypes below them, are to get
    # us started when we come back here later to feed the process
    # output to high level loggin somehow.
    #
    # In a successful launch, we see:
    # - connectionMade (at which point we closeStdin)
    # - inConnectionLost (which is then expected)
    # - childDataReceived(counter, message), output from the script.
    # - later, when process exits: processExited(status).  Status is some
    #   kind of object that knows the return code...
    # In a failed launch, it's the same except note that:
    # - The childDataReceived message contains the python traceback, on,
    #   e.g. realm error.  +1 - Informative.
    # - The processExited(status) knows the return code was not 0.
    #
    # Note that you implement childDataReceived instead of
    # "outReceived" and "errReceived".
    status = None, None
    killed = False
    instance_id = '(none)'
    def connectionMade(self):
        self.transport.closeStdin()
    def inConnectionLost(self):
        pass
    def processExited(self, status):
        print('%s.status:' % self.instance_id, status)
        self.status = status, time.time()
    def outReceived(self, data):
        print('%s.stdin:' % self.instance_id, data)
    def errReceived(self, data):
        print('%s.stderr:' % self.instance_id, data)


if __name__ == '__main__':
    parser = site_config.add_arguments()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default='down',
                        choices=['up', 'down'])
    args = parser.parse_args()
    site_config.reparse_args(args, 'HostMaster')

    # To reduce "try again" noise, don't tell Registry about HostMaster.
    args.registry_address = 'none'

    agent, runner = ocs_agent.init_site_agent(args)
    host_master = HostMaster(agent)

    startup_params = {'requests': [('all', args.initial_state)]}
    agent.register_process('master',
                           host_master.master_process,
                           host_master.master_process_stop,
                           blocking=False,
                           startup=startup_params)
    agent.register_task('update', host_master.update_task, blocking=False)
    agent.register_task('die', host_master.die, blocking=False)
    runner.run(agent, auto_reconnect=True)

