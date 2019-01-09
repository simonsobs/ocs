import time, threading
import numpy as np
from ocs import ocs_agent, site_config, client_t
import os
if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core

# import op_model as opm
from autobahn.wamp.exception import ApplicationError


class DataAggregator:

    def __init__(self, agent):

        self.agent = agent
        self.log = agent.log

        self.subscribed_feeds = []

        self.buffers = {}
        self.buffer_start_times = {}

        self.aggregate = False

        self.filename = ""
        self.file = None

        self.registered = False



    def add_feed(self, agent_address, feed_name):
        """
        Subscribes to aggregated feed

        Args:
            agent_address (string):
                agent address of the feed.

            feed_name (string):
                name of the feed.
        """

        def _data_handler(_data):
            """Callback whenever data is published to an aggregated feed"""
            if not self.aggregate:
                return

            data, feed = _data
            addr = feed["address"]

            if feed['buffered']:
                # If data is buffered by the Feed, immediately write it to a frame.
                self.write_frame_to_file(addr, data)

            else:
                # If not, the aggregator needs to buffer the data itself.
                current_time = time.time()
                if not self.buffers[addr]:
                    self.buffer_start_times[addr] = current_time

                if current_time - self.buffer_start_times[addr] > feed["buffer_time"]:
                    self.write_frame_to_file(addr, self.buffers[addr])
                    self.buffer_start_times[addr] = current_time
                    self.buffers[addr] = []

                self.buffers[addr].append(data)

        feed_address = "{}.feeds.{}".format(agent_address, feed_name)
        if feed_address in self.subscribed_feeds:
            return

        self.agent.subscribe_to_feed(agent_address, feed_name, _data_handler)
        self.subscribed_feeds.append(feed_address)
        self.buffers[feed_address] = []
        self.log.info("Subscribed to feed {}".format(feed_address))

    def initialize(self, session, params={}):
        """
        TASK: Registers the aggregator and subscribes to *agent_activity* feed.
        """

        # Only subscribes to registry feeds if agent is registered.
        if not self.agent.registered:
            return True, "Initialized Aggregator"

        reg_address = self.agent.site_args.registry_address

        dump_agents_t = client_t.TaskClient(session.app,
                                            reg_address,
                                            'dump_agent_info')

        def _new_agent_handler(_data):
            """Callback for whenever an agent is published to agent_activity"""
            (action, agent_data), feed_data = _data

            if action == "removed":
                return

            feeds = agent_data.get("feeds")
            if feeds is None:
                return

            for feed in agent_data["feeds"]:
                if feed['agg_params'].get("aggregate", False):
                    self.add_feed(feed["agent_address"], feed["feed_name"])

        self.agent.subscribe_to_feed(reg_address,
                                     'agent_activity',
                                     _new_agent_handler)

        session.call_operation(dump_agents_t.start)
        return True, "Initialized Aggregator"


    # Task to subscribe to data feeds
    def add_feed_task(self, sessions, params=None):
        """
        TASK: Subscribes to specified feed.

        Args:
            agent_address (string):
                agent address of the feed.

            feed_name (string):
                name of the feed.
        """
        if params is None:
            params = {}

        agent_address = params["agent_address"]
        feed_name = params["feed_name"]

        feed_address = "{}.feeds.{}".format(agent_address, feed_name)
        if feed_address in self.incoming_data.keys():
            return False, "Already subscribed to feed {}".format(feed_address)

        self.add_feed(agent_address, feed_name)
        return True, 'Subscribed to data feeds.'


    def write_frame_to_file(self, feed_address, buffer):
        """
            Writes a feed buffer to G3Frame.
        """


        self.log.info("Writing feed {} to frame".format(feed_address))

        frame = core.G3Frame(core.G3FrameType.Housekeeping)
        frame["feed"] = feed_address

        tods = {}
        timestamps = {}

        # Creates tods and timestamps from frame data
        for data_point in buffer:
            for key, val in data_point.items():
                if key in tods.keys():
                    tods[key].append(val[1])
                    timestamps[key].append(val[0])
                else:
                    tods[key] = [val[1]]
                    timestamps[key] = [val[0]]

        tod_map = core.G3TimestreamMap()
        timestamp_map = core.G3TimestreamMap()

        for key in tods:
            tod_map[key] = core.G3Timestream(tods[key])
            timestamp_map[key] = core.G3Timestream(timestamps[key])

        frame["TODs"] = tod_map
        frame["Timestamps"] = timestamp_map

        # Writes frame to file
        self.file(frame)


    def start_file(self):
        """
        Starts new G3File with filename ``self.filename``.
        """
        print("Creating file: {}".format(self.filename))
        self.file = core.G3Writer(filename=self.filename)
        return

    def end_file(self):
        """
        Ends current G3File with EndProcessing frame.
        """

        for k, v in self.buffers.items():
            # Writes all non-empty buffers to File
            if v:
                self.write_frame_to_file(k, v)
                self.buffers[k] = []

        self.file(core.G3Frame(core.G3FrameType.EndProcessing))

        print("Closing file: {}".format(self.filename))
        return

    def start_aggregate(self, session, params={}):
        """
        PROCESS: Starts the aggregation process.

        Args:
            time_per_file (int, optional):
                Specifies how much time should elapse before starting a new
                file (in seconds). Defaults to 1 hr.

            time_per_frame (int, optional):
                Specifies how much time should elapse before starting a new
                frame (in seconds). Defaults to 10 minutes.

            data_dir (string, optional):
                Path of directory to store data. Defaults to 'data/'.
        """

        if params is None:
            print("No params specified")
            params = {}

        time_per_file = params.get("time_per_file", 60 * 60) # [s]
        time_per_frame = params.get("time_per_frame", 60 * 10)  # [s]
        data_dir = params.get("data_dir", "data/")

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.log.info("Starting data aggregation in directory {}".format(data_dir))

        session.set_status('running')

        new_file_time = True

        self.aggregate = True
        while self.aggregate:

            if new_file_time:
                if self.file is not None:
                    self.end_file()

                file_start_time = time.time()
                time_string = time.strftime("%Y-%m-%d_T_%H:%M:%S", time.localtime(file_start_time))
                self.filename = os.path.join(data_dir, "{}.g3".format(time_string))
                self.start_file()

                session.add_message('Starting a new DAQ file: %s' % self.filename)

            time.sleep(.1)
            # Check if its time to write new frame/file
            new_file_time = (time.time() - file_start_time) > time_per_file

        self.end_file()
        return True, 'Acquisition exited cleanly.'
            
    def stop_aggregate(self, session, params=None):
        self.aggregate = False
        return (True, "Stopped aggregation")


if __name__ == '__main__':

    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'AggregatorAgent')

    agent, runner = ocs_agent.init_site_agent(args)

    data_aggregator = DataAggregator(agent)

    agent.register_task('initialize', data_aggregator.initialize)
    agent.register_task('subscribe', data_aggregator.add_feed_task)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
