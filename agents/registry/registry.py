from ocs import ocs_agent, site_config
import time
from twisted.internet import task

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

    def _monitor_active_agents(self):
        """
            Deletes agent from active_agents if a heartbeat isn't heard in
            *self.agent_timeout* seconds. This is called once a second.
        """
        current_time = time.time()
        agents_to_remove = []
        for address, agent in self.active_agents.items():
            if (current_time - agent["last_heartbeat"]) > self.agent_timeout:
                agents_to_remove.append(address)

        for address in agents_to_remove:
            del(self.active_agents[address])
            self.log.info("Agent {} has been removed due to inactivity".format(address))
            self.agent.publish_to_feed("agent_activity", ("removed", agent))


    def _register_heartbeat(self, data):
        """Registers the heartbeats of active_agents"""
        _, feed_data = data
        agent_address = feed_data['agent_address']
        if agent_address in self.active_agents.keys():
            self.active_agents[agent_address]['last_heartbeat'] = time.time()


    def register_agent(self, session, agent_data):
        """
        Adds agent to list of active agents and subscribes to heartbeat feed.

        Args
            agent_data (dict):  Encoded agent data.
                Must contain at least agent address.
        """

        address = agent_data['agent_address']
        action = "added"
        if address in self.active_agents.keys():
            self.log.error("Address {} is already registered, agent info is being updated".format(address))
            action = "updated"

        self.active_agents[address] = agent_data
        self.active_agents[address]["time_registered"] = time.time()
        self.active_agents[address]["last_heartbeat"] = time.time()
        self.agent.subscribe_to_feed(address, 'heartbeat', self._register_heartbeat)


        self.log.info("Registered agent {}".format(address))
        session.add_message("Registered agent {}".format(address))
        self.agent.publish_to_feed("agent_activity", (action, agent_data));

        return True, "Registered agent {}".format(address)

    def unregister_agent(self, session, agent_data):
        """
        Removes agent from list of active agents.

        Args
            agent_data (dict):  Encoded agent data.
                Must contain at least agent address.
        """

        agent_address = agent_data["address"]
        action = "removed"
        try:
            del self.active_agents[agent_address]
            self.log.info("Agent {} has been removed".format(agent_address))
            session.add_message("Agent {} has been removed".format(agent_address))
            self.agent.publish_to_feed("agent_activity", (action, agent_data))

        except KeyError:
            self.log.error("{} is not a registered agent".format(agent_address))
            return False, "Agent not registered"

        return True, "Removed agent {}".format(agent_address)

    def dump_agent_info(self, session, params = {}):
        """
        Tells the registry agent to dump status info for all active agent to
        *agent_activity* feed.
        """
        action = "status"
        for address, agent in self.active_agents.items():
            self.agent.publish_to_feed("agent_activity", (action, agent))

        return True, "Dumped agent info"


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'RegistryAgent')

    agent, runner = ocs_agent.init_site_agent(args)
    registry = Registry(agent)

    agent.register_task('dump_agent_info', registry.dump_agent_info)
    agent.register_task('register_agent', registry.register_agent)
    agent.register_task('unregister_agent', registry.unregister_agent)

    # Starts looping call that calls _motitor_active_agent every second
    loop_call = task.LoopingCall(registry._monitor_active_agents)
    loop_call.start(1)

    runner.run(agent, auto_reconnect=True)

