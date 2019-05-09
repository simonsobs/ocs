from ocs import ocs_agent, site_config
import time
from twisted.internet import task
from threading import Lock


class RegisteredAgent:
    def __init__(self, agent_encoded):
        self.encoded = agent_encoded

        for key in ['agent_session_id']:
            setattr(self, key, self.encoded[key])

        self.time_registered = time.time()
        self.last_heartbeat = time.time()


class Registry:
    """
    The Registry agent is in charge of keeping track of which agents are
    currently running, and publishing this data to the *agent_activity*
    feed.
    """
    def __init__(self, agent):
        self.log = agent.log
        self.agent = agent

        # Dict containing agent_data for each registered agent
        self.active_agents = {}
        self.agent_timeout = 5.0 # Removes agent after 5 seconds of no heartbeat.

        self.agent.register_feed("agent_activity")

        self.lock = Lock()

    def _monitor_active_agents(self):
        """
            Deletes agent from active_agents if a heartbeat isn't heard in
            *self.agent_timeout* seconds. This is called once a second.
        """
        current_time = time.time()
        agents_to_remove = []
        for address, agent in self.active_agents.items():

            # For some reason the registry has been unable to listen to its
            # own heartbeat... This makes it so that the registry can't
            # unregister itself.
            if address == self.agent.agent_address:
                continue
            if (current_time - agent.last_heartbeat) > self.agent_timeout:
                agents_to_remove.append(address)
        with self.lock:
            for address in agents_to_remove:
                if self.remove_agent(address):
                    self.log.info("Agent {} has been removed due to inactivity"
                                  .format(address))

    def _register_heartbeat(self, data):
        """Registers the heartbeats of active_agents"""
        _, feed_data = data
        agent_address = feed_data['agent_address']
        if agent_address in self.active_agents.keys():
            self.active_agents[agent_address].last_heartbeat = time.time()

    def remove_agent(self, agent_address):
        """
        Removes agent from the registry and publishes removal to the status feed.

        Args
            agent_address (string): address of agent to be removed.
        """
        agent = self.active_agents.get(agent_address)
        if not agent:
            self.log.warn("Tried to remove {}, but agent was not registered"
                          .format(agent_address))
            return False

        self.log.info("Removing agent {}".format(agent_address))
        self.agent.publish_to_feed("agent_activity", ("removed", agent.encoded))
        del(self.active_agents[agent_address])
        return True

    def register_agent(self, session, agent_data):
        """
        TASK: Adds agent to list of active agents and subscribes to heartbeat feed.

        Args
            agent_data (dict):  Encoded agent data.
                Must contain at least agent address.
        """

        address = agent_data['agent_address']

        action = "added"
        if address in self.active_agents.keys():
            if agent_data['agent_session_id'] != self.active_agents[address].agent_session_id:
                self.log.info("Address {} is already registered. Removing old"
                              "instance and replacing it with new one"
                              .format(address))

                with self.lock:
                    self.remove_agent(address)
            else:
                self.log.info("Agent with session id {} has already been registered."
                              .format(agent_data['agent_session_id']))
                return False, "Agent already registered with session id {}".format(agent_data['agent_session_id'])

        with self.lock:
            self.active_agents[address] = RegisteredAgent(agent_data)

        self.agent.subscribe_to_feed(address, 'heartbeat', self._register_heartbeat)

        self.log.info("Registered agent {}".format(address))
        session.add_message("Registered agent {}".format(address))
        self.agent.publish_to_feed("agent_activity", (action, agent_data));

        return True, "Registered agent {}".format(address)

    def dump_agent_info(self, session, params = {}):
        """
        Tells the registry agent to dump status info for all active agent to
        *agent_activity* feed.
        """
        action = "status"
        for address, agent in self.active_agents.items():
            self.agent.publish_to_feed("agent_activity", (action, agent.encoded))

        return True, "Dumped agent info"


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'RegistryAgent')

    agent, runner = ocs_agent.init_site_agent(args)
    registry = Registry(agent)

    agent.register_task('dump_agent_info', registry.dump_agent_info)
    agent.register_task('register_agent', registry.register_agent, blocking=False)

    # Starts looping call that calls _motitor_active_agent every second
    loop_call = task.LoopingCall(registry._monitor_active_agents)
    loop_call.start(1)

    runner.run(agent, auto_reconnect=True)

