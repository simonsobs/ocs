import time
import txaio

from ocs import ocs_agent, site_config

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


class DemoAgent:
    def __init__(self, agent):
        self.agent = agent
        self.log = agent.log
        self.run_process = None

    # Tasks
    def demo_task(self, session, params):
        self.log.info('hello task')

        return True, 'ran task'

    # Processes
    def demo_process(self, session, params):
        session.set_status('running')

        self.run_process = True

        while self.run_process:
            self.log.info('hello process')
            time.sleep(10)

        return True, 'process exited cleanly.'

    def _stop_demo_process(self, session, params):
        if self.run_process:
            self.run_process = False
            return True, 'stopped process'
        else:
            return False, 'process not running'


if __name__ == '__main__':
    # Start logging
    txaio.start_logging(level='info')

    # Create Agent and ApplicationRunner
    args = site_config.parse_args(agent_class='DemoAgent')
    agent, runner = ocs_agent.init_site_agent(args)

    # Instantiate agent
    demo = DemoAgent(agent)

    # Register Tasks + processes
    agent.register_task('demo_task', demo.demo_task)
    agent.register_process('demo_process',
                           demo.demo_process,
                           demo._stop_demo_process)

    # Run the Agent
    runner.run(agent, auto_reconnect=True)
