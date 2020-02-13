import time
import queue
import argparse

from ocs import ocs_agent, site_config
from ocs.agent.aggregator import Aggregator


class AggregatorAgent:
    """
    This class provide a WAMP wrapper for the data aggregator. The run function
    and the data handler **are** thread-safe, as long as multiple run functions
    are not started at the same time, which should be prevented through OCSAgent.

    Args:
        agent (OCSAgent):
            OCS Agent object
        args (namespace):
            args from the function's argparser.

    Attributes:
        time_per_file (int):
            Time (sec) before files should be rotated.
        data_dir (path):
            Path to the base directory where data should be written.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        incoming_data (queue.Queue):
            Thread-safe queue where incoming (data, feed) pairs are stored before
            being passed to the Aggregator.
        loop_time (float):
            Time between iterations of the run loop.
    """
    def __init__(self, agent, args):
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log

        self.time_per_file = int(args.time_per_file)
        self.data_dir = args.data_dir

        self.aggregate = False
        self.incoming_data = queue.Queue()
        self.loop_time = 1

        # SUBSCRIBES TO ALL FEEDS!!!!
        # If this ends up being too much data, we can add a tag '.record'
        # at the end of the address of recorded feeds, and filter by that.
        self.agent.subscribe_on_start(self.enqueue_incoming_data,
                                      'observatory..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record',
                                    self.start_aggregate, self.stop_aggregate,
                                    startup=record_on_start)

    def enqueue_incoming_data(self, _data):
        """
        Data handler for all feeds. This checks to see if the feeds should
        be recorded, and if they are it puts them into the incoming_data queue
        to be processed by the Aggregator during the next run iteration.
        """
        data, feed = _data

        if not feed['record'] or not self.aggregate:
            return

        self.incoming_data.put((data, feed))

    def start_aggregate(self, session: ocs_agent.OpSession, params=None):
        """
        Process for starting data aggregation. This process will create an
        Aggregator instance, which will collect and write provider data to disk
        as long as this process is running.
        """
        session.set_status('starting')
        self.aggregate = True

        aggregator = Aggregator(self.incoming_data, self.time_per_file, self.data_dir)

        session.set_status('running')
        while self.aggregate:
            time.sleep(self.loop_time)
            aggregator.run()

        aggregator.close()

        return True, "Aggregation has ended"

    def stop_aggregate(self, session, params=None):
        session.set_status('stopping')
        self.aggregate = False
        return True, "Stopping aggregation"


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--data-dir', required=True,
                        help="Base directory to store data. "
                             "Subdirectories will be made here.")
    pgroup.add_argument('--initial-state',
                        default='idle',choices=['idle', 'record'],
                        help="Initial state of argument parser. Can be either"
                             "idle or record")
    pgroup.add_argument('--time-per-file', default='3600',
                        help="Time per file in seconds. Defaults to 1 hr")

    return parser


if __name__ == '__main__':
    parser = make_parser()
    args = site_config.parse_args(agent_class='AggregatorAgent',
                                  parser=parser)
    agent, runner = ocs_agent.init_site_agent(args)

    data_aggregator = AggregatorAgent(agent, args)
    runner.run(agent, auto_reconnect=True)
