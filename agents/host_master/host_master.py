from ocs import ocs_agent, site_config
import time

from twisted.internet import reactor, task, threads
from twisted.internet import protocol
from twisted.internet.defer import inlineCallbacks, Deferred, DeferredList, FirstError
from autobahn.twisted.util import sleep as dsleep

import threading
import socket
import os, sys

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
        self.pid_cache = {} # key is (class_name, instance_id)
        self.site_file = None
 
    def _init_instance_list(self, session):
        """
        Parse the site config and register all of this host's instances in
        pid_cache.
        """
        # Load site config file.
        site, _, _ = site_config.get_config(
            self.agent.site_args, '*control*')
        self.site_config_file = site.source_file

        this_host = socket.gethostname()
        for k,hc in site.hosts.items():
            if k == this_host:
                break
        else:
            session.add_message('Entry for host not found: %s.' % this_host)
            return True, 'No action taken.'

        # Add plugin paths and scan.
        for p in hc.agent_paths:
            if not p in sys.path:
                sys.path.append(p)
        site_config.scan_for_agents()
        
        # Loop through all Agent instances on this host and add them
        # to pid_cache.
        for inst in hc.instances:
            class_name, instance_id = inst['agent-class'], inst['instance-id']
            if class_name == 'HostMaster':
                continue
            key = (class_name, instance_id)
            if not key in self.pid_cache:
                self.pid_cache[key] = None

        return True, ''

    def _launch_instance(self, pid_key, script_file, site_file, instance_id):
        """
        Launch an Agent instance using reactor.spawnProcess.  The
        ProcessProtocol, which holds communication pathways to the
        process, will be registered in self.pid_cache.  The site_file
        and instance_id are passed on the command line; this means
        that any weird config overrides passed to this HostMaster are
        not propagated.

        Because of the use of spawnProcess, this should be called in
        the reactor thread.
        """
        pyth = sys.executable
        cmd = [pyth, script_file,
               '--instance-id', instance_id,
               '--site-file', site_file]
        prot = AgentProcessProtocol()
        reactor.spawnProcess(prot, cmd[0], cmd[:], env=os.environ)
        self.pid_cache[pid_key] = prot

    def _terminate_instance(self, key):
        """
        Use the ProcessProtocol to request the Agent instance to exit.
        """
        prot = self.pid_cache.get(key) # Get the ProcessProtocol.
        if prot is None:
            return True, 'Instance was not running.'
        if prot.killed:
            return True, 'Instance already has kill set.'
        prot.killed = True
        prot.transport.signalProcess('KILL')
        return True, 'Kill requested.'
        
    @inlineCallbacks
    def master_process(self, session, params=None):
        """
        When running, the master_process launches and tries to keep alive
        all of the Agent instances listed on this host.

        Presently, the policy for restarting agents if they fail is
        hard-coded and trivial.

        When the process is signaled to exit, it will try to kill all
        the agents it is managing.
        """
        self.running = True
        session.set_status('running')

        # Update the list of Agent instances.
        self._init_instance_list(session)
        self.database = {
            key: {'next_action': 'start',
                  'class_name': key[0],
                  'instance_id': key[1],
                  'full_name': ('%s:%s' % tuple(key)),
                  'agent_script': site_config.agent_script_reg.get(key[0])
            } for key in self.pid_cache.keys() }
        
        any_jobs = False
        dying_words = ['idle', 'kill', 'wait_dead']  #allowed during shutdown

        while self.running or any_jobs:

            sleep_time = 1.
            any_jobs = False

            for key, prot in self.pid_cache.items():
                # State machine.
                db = self.database[key]

                if not self.running and db['next_action'] not in dying_words:
                    db['next_action'] = 'kill'
                    
                if db['next_action'] == 'idle':
                    pass
                elif db['next_action'] == 'start_at':
                    if time.time() >= db['at']:
                        db['next_action'] = 'start'
                    else:
                        sleep_time = min(sleep_time, db['at'] - time.time())
                elif db['next_action'] == 'start':
                    # Launch.
                    if db['agent_script'] is None:
                        session.add_message('No Agent script registered for '
                                            'class: {class_name}'.format(**db))
                        db['next_action'] = 'idle'
                    else:
                        session.add_message(
                            'Launching {full_name}'.format(**db))
                        self.pid_cache[key] = None
                        reactor.callFromThread(
                            self._launch_instance, key, db['agent_script'],
                            self.site_config_file, db['instance_id'])
                        db['next_action'] = 'monitor'
                elif db['next_action'] == 'monitor':
                    stat, t = prot.status
                    if stat is not None:
                        session.add_message('Detected exit of {full_name} '
                                            'with code {stat}.'.format(stat=stat, **db))
                        db['next_action'] = 'start_at'
                        db['at'] = time.time() + 3
                    self.pid_cache[key]
                elif db['next_action'] == 'kill':
                    session.add_message('Requesting termination of '
                                        '{full_name}'.format(**db))
                    self._terminate_instance(key)
                    db['next_action'] = 'wait_dead'
                    db['at'] = time.time() + 5
                elif db['next_action'] == 'wait_dead':
                    if prot is None:
                        stat, t = 0, None
                    else:
                        stat, t = prot.status
                    if stat is not None:
                        db['next_action'] = 'idle'
                    elif time.time() >= db['at']:
                        if stat is None:
                            session.add_message('Agent instance {full_name} '
                                                'refused to die.'.format(**db))
                            db['next_action'] = 'idle'
                    else:
                        sleep_time = min(sleep_time, db['at'] - time.time())

                any_jobs = (any_jobs or (db['next_action'] != 'idle'))

            yield dsleep(max(sleep_time, .001))
        return True, 'Exited.'

    def master_process_stop(self, session, params=None):
        session.set_status('stopping')
        self.running = False
        return True, 'Stop initiated.'


class AgentProcessProtocol(protocol.ProcessProtocol):
    # See https://twistedmatrix.com/documents/current/core/howto/process.html
    status = None, None
    killed = False
    def processExited(self, status):
        self.status = status, time.time()


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'HostMaster')

    agent, runner = ocs_agent.init_site_agent(args)
    host_master = HostMaster(agent)

    agent.register_process('master',
                           host_master.master_process,
                           host_master.master_process_stop,
                           blocking=False)

    runner.run(agent, auto_reconnect=True)

