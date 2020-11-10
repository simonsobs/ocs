from ocs import ocs_agent, site_config
import time
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep
from collections import defaultdict
from enum import Enum


class RegisteredAgent:
    """
        Contains data about registered agents.

        Attributes:
            expired (bool):
                True if agent has not been updated in Registry.agent_timeout seconds.
            time_expired (float, optional):
                ctime at which the agent expired. This will be None if the agent
                is not expired.
            last_updated (float):
                ctime at which the agent was last updated
    """
    def __init__(self):
        self.expired = False
        self.time_expired = None
        self.last_updated = time.time()
        self.op_codes = {}

    def refresh(self, op_codes=None):
        self.expired = False
        self.time_expired = None
        self.last_updated = time.time()

        if op_codes:
            self.op_codes.update(op_codes)

    def expire(self):
        self.expired = True
        self.time_expired = time.time()
        for k in self.op_codes:
            self.op_codes[k] = ocs_agent.OpCode.EXPIRED.value

    def encoded(self):
        return {
            'expired': self.expired,
            'time_expired': self.time_expired,
            'last_updated': self.last_updated,
            'op_codes': self.op_codes,
        }


class Registry:
    """
        The Registry agent is in charge of keeping track of which agents are
        currently running. It has a single process "main" that loops and keeps track
        of when agents expire. This agent subscribes to all heartbeat feeds, 
        so no additional function calls are required to register an agent.

        A list of agent statuses is maintained in the "main" process's session.data
        object.

        Args: 
            agent (OCSAgent):
                the ocs agent object

        Attributes:
            registered_agents (defaultdict):
                A defaultdict of RegisteredAgent objects, which contain whether 
                the agent has expired, the time_expired, and the last_updated 
                time. 
            agent_timeout (float):
                The time an agent has between heartbeats before being marked
                as expired.
    """
    def __init__(self, agent):
        self.log = agent.log
        self.agent = agent

        # Dict containing agent_data for each registered agent
        self.registered_agents = defaultdict(RegisteredAgent)
        self.agent_timeout = 5.0 # Removes agent after 5 seconds of no heartbeat.

        self.agent.subscribe_on_start(
            self._register_heartbeat, 'observatory..feeds.heartbeat',
            options={'match': 'wildcard'}
        )

        agg_params = {
            'frame_length': 30*60,
            'fresh_time': 10,
        }
        self.agent.register_feed('agent_operations', record=True,
                                 agg_params=agg_params, buffer_time=0)



    def _register_heartbeat(self, _data):
        """ 
            Function that is called whenever a heartbeat is received from an agent.
            It will update that agent in the Registry's registered_agent dict.
        """
        op_codes, feed = _data
        self.registered_agents[feed['agent_address']].refresh(op_codes=op_codes)

    @inlineCallbacks
    def main(self, session: ocs_agent.OpSession, params=None):
        """
            Main run process for the Registry agent. This will loop and keep track of
            which agents have expired. It will keep track of current active agents
            in the session.data variable so it can be seen by clients.

            The session.data object for this process will be a dictionary containing
            the encoded RegisteredAgent object for each agent observed during the
            lifetime of the registry. For instance, this might look like
            
            >>> session.data
            {'observatory.aggregator': 
                {'expired': False,
                 'last_updated': 1583179794.5175,
                 'time_expired': None},
             'observatory.faker1': 
                {'expired': False,
                 'last_updated': 1583179795.072248,
                 'time_expired': None},
             'observatory.faker2': 
                {'expired': True,
                 'last_updated': 1583179777.0211036,
                 'time_expired': 1583179795.3862052}}
        """

        session.set_status('starting')
        self._run = True

        session.set_status('running')
        while self._run:
            yield dsleep(1)

            for k, agent in self.registered_agents.items():
                if time.time() - agent.last_updated > self.agent_timeout:
                    agent.expire()

            session.data = {
                k: agent.encoded() for k, agent in self.registered_agents.items()
            }

            for addr, agent in self.registered_agents.items():
                _addr = addr.replace('.', '_')
                _addr = _addr.replace('-', '_')
                msg = {
                    'block_name': _addr,
                    'timestamp': time.time(),
                    'data': {
                        f'{_addr}_{op_name}': op_code
                        for op_name, op_code in agent.op_codes.items()
                    }
                }
                self.agent.publish_to_feed('agent_operations', msg)

        return True, "Stopped registry main process"

    def stop(self, session, params=None):
        """Stop function for the 'run' process."""
        session.set_status('stopping')
        self._run = False

    def _register_agent(self, session, agent_data):
        self.log.warn(
            "Warning!!! The register_agent task has been deprecated. Agent '{}' "
            "is using an out of date version of ocs or socs!!"
            .format(agent_data['agent_address'])
        )

        return True, "'register_agent' is deprecated"


if __name__ == '__main__':
    args = site_config.parse_args(agent_class='RegistryAgent',
                                  parser=None)

    agent, runner = ocs_agent.init_site_agent(args)
    registry = Registry(agent)

    agent.register_process('main', registry.main, registry.stop, blocking=False, startup=True)
    agent.register_task('register_agent', registry._register_agent, blocking=False)
    
    runner.run(agent, auto_reconnect=True)

