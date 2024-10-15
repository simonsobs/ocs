from ocs import ocs_agent, site_config
from ocs.base import OpCode
import time
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep
from ocs.ocs_feed import Feed
import argparse


class RegisteredAgent:
    """
        Contains data about registered agents.

        Args:
            feed (dict): Encoded :class:`ocs.ocs_feed.Feed`.

        Attributes:
            expired (bool):
                True if agent has not been updated in Registry.agent_timeout seconds.
            time_expired (float, optional):
                ctime at which the agent expired. This will be None if the agent
                is not expired.
            last_updated (float):
                ctime at which the agent was last updated
            op_codes (dict):
                Dictionary of operation codes for each of the agent's
                operations. For details on what the operation codes mean, see
                docs from the ``ocs_agent`` module
    """

    def __init__(self, feed):
        self.expired = False
        self.time_expired = None
        self.last_updated = time.time()
        self.op_codes = {}
        self.agent_class = feed.get('agent_class')
        self.agent_address = feed['agent_address']

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
            self.op_codes[k] = OpCode.EXPIRED.value

    def encoded(self):
        return {
            'expired': self.expired,
            'time_expired': self.time_expired,
            'last_updated': self.last_updated,
            'op_codes': self.op_codes,
            'agent_class': self.agent_class,
            'agent_address': self.agent_address,
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

    def __init__(self, agent, args):
        self.log = agent.log
        self.agent = agent
        self.wait_time = args.wait_time

        # Tracking for 'main' Process
        self._run = False

        # Dict containing agent_data for each registered agent
        self.registered_agents = {}
        self.agent_timeout = 5.0  # Removes agent after 5 seconds of no heartbeat.

        self.agent.subscribe_on_start(
            self._register_heartbeat, f'{args.address_root}..feeds.heartbeat',
            options={'match': 'wildcard'}
        )

        agg_params = {
            'frame_length': 60,
        }
        self.agent.register_feed('agent_operations', record=True,
                                 agg_params=agg_params, buffer_time=0)

    def _register_heartbeat(self, _data):
        """
            Function that is called whenever a heartbeat is received from an agent.
            It will update that agent in the Registry's registered_agent dict.
        """
        op_codes, feed = _data
        addr = feed['agent_address']
        if addr not in self.registered_agents:
            self.registered_agents[addr] = RegisteredAgent(feed)

        reg_agent = self.registered_agents[addr]
        publish = op_codes != reg_agent.op_codes
        self.registered_agents[addr].refresh(op_codes=op_codes)
        if publish:
            self._publish_agent_ops(reg_agent)

    def _publish_agent_ops(self, reg_agent):
        """Publish a registered agent's OpCodes.

        Args:
            reg_agent (RegisteredAgent): The registered agent.

        """
        addr = reg_agent.agent_address
        self.log.debug(addr)
        for op_name, op_code in reg_agent.op_codes.items():
            field = f'{addr}_{op_name}'
            field = field.replace('.', '_')
            field = field.replace('-', '_')
            field = Feed.enforce_field_name_rules(field)
            try:
                Feed.verify_data_field_string(field)
            except ValueError as e:
                self.log.warn(f"Improper field name: {field}\n{e}")
                continue
            msg = {'block_name': field,
                   'timestamp': time.time(),
                   'data': {field: op_code}}
            self.agent.publish_to_feed('agent_operations', msg)

    @ocs_agent.param('test_mode', default=False, type=bool)
    @inlineCallbacks
    def main(self, session: ocs_agent.OpSession, params):
        """main(test_mode=False)

        **Process** - Main run process for the Registry agent. This will loop
        and keep track of which agents have expired. It will keep track of
        current active agents in the session.data variable so it can be seen by
        clients.

        Parameters:
            test_mode (bool, optional): Run the main Process loop only once.
                This is meant only for testing. Default is False.

        Notes:
            The session data object for this process will be a dictionary containing
            the encoded RegisteredAgent objects for each agent observed during the
            lifetime of the Registry. For instance, this might look like::

                >>> response.session['data']
                {
                  "observatory.aggregator": {
                    "expired": False,
                    "time_expired": None,
                    "last_updated": 1669925713.4082503,
                    "op_codes": {
                      "record": 3
                    },
                    "agent_class": "AggregatorAgent",
                    "agent_address": "observatory.aggregator"
                  },
                  "observatory.fake-hk-agent-01": {
                    "expired": False,
                    "time_expired": None,
                    "last_updated": 1669925945.7575383,
                    "op_codes": {
                      "acq": 3,
                      "set_heartbeat": 1,
                      "delay_task": 1
                    },
                    "agent_class": "FakeDataAgent",
                    "agent_address": "observatory.fake-hk-agent-01"
                  }
                }

        """
        self._run = True

        last_publish = time.time()
        while self._run:
            yield dsleep(1)

            now = time.time()
            for k, agent in self.registered_agents.items():
                if now - agent.last_updated > self.agent_timeout:
                    agent.expire()

            session.data = {
                k: agent.encoded() for k, agent in self.registered_agents.items()
            }

            if now - last_publish >= self.wait_time:
                last_publish = now
                for agent in self.registered_agents.values():
                    self._publish_agent_ops(agent)

            if params['test_mode']:
                break

        return True, "Stopped registry main process"

    @inlineCallbacks
    def _stop_main(self, session, params):
        """Stop function for the 'main' process."""
        yield
        if self._run:
            session.set_status('stopping')
            self._run = False
            return True, 'requested to stop main process'
        else:
            return False, 'main process not currently running'

    def _register_agent(self, session, agent_data):
        self.log.warn(
            "Warning!!! The register_agent task has been deprecated. Agent '{}' "
            "is using an out of date version of ocs or socs!!"
            .format(agent_data['agent_address'])
        )

        return True, "'register_agent' is deprecated"


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--wait-time', type=float, default=30.,
                        help='Sleep time for main loop')
    return parser


def main(args=None):
    parser = make_parser()
    args = site_config.parse_args(agent_class='RegistryAgent',
                                  parser=parser,
                                  args=args)

    agent, runner = ocs_agent.init_site_agent(args)
    registry = Registry(agent, args)

    agent.register_process('main', registry.main, registry._stop_main, blocking=False, startup=True)
    agent.register_task('register_agent', registry._register_agent, blocking=False)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
