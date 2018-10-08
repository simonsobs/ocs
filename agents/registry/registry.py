from ocs import ocs_agent, site_config
import time

class Registry:
    def __init__(self, agent):
        self.log = agent.log
        self.agent = agent

        # Dict containing agent_data for each registered agent
        self.active_agents = {}

        self.agent.register_feed("new_agent")
        self.agent.register_feed("removed_agent")

    def register_agent(self, session, agent_data):
        """
        Adds agent to list of active_agent.
        :param agent_data: Encoded agent data.
        """
        address = agent_data['address']

        if address in self.active_agents.keys():
            self.log.error("Address {} is already registered, agent info is being updated".format(address))

        self.active_agents[address] = agent_data
        self.active_agents[address]["time_registered"] = time.time()
        self.log.info("Registered agent {}".format(address))
        session.post_message("Registered agent {}".format(address))
        self.agent.publish_to_feed("new_agent", agent_data)
        return True, "Registered agent {}".format(address)

    def remove_agent(self, session, agent_address):
        """
        Removes agent from list of active agents.
        :param agent_address: Address of agent to remove
        """
        print("In Remove agent")
        try:
            del self.active_agents[agent_address]
            self.log.info("Agent {} has been removed".format(agent_address))
            session.post_message("Agent {} has been removed".format(agent_address))
            self.agent.publish_to_feed("removed_agent", agent_address)

        except KeyError:
            self.log.error("{} is not a registered agent".format(agent_address))
            return False, "Agent not registered"

        return True, "Removed agent {}".format(agent_address)


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'RegistryAgent')

    agent, runner = ocs_agent.init_site_agent(args)
    registry = Registry(agent)

    agent.register_task('register_agent', registry.register_agent)
    agent.register_task('remove_agent', registry.remove_agent)

    runner.run(agent, auto_reconnect=True)

