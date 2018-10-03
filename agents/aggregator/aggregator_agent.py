import time, threading
import numpy as np
from ocs import ocs_agent, site_config
from spt3g import core
# import op_model as opm


class DataAggregator:

    def __init__(self, agent):

        self.agent = agent
        self.log = agent.log
        self.incoming_data = {}
        self.aggregate = False

        self.filename = ""
        self.file = None


    # Task to subscribe to data feeds
    def subscribe_to_feed(self, sessions, feed):

        if feed in self.incoming_data.keys():
            return False, "Already subscribed to feed {}".format(feed)

        def handler(data):
            # Do we want to save data before aggregate starts? Probably doesn't matter
            if self.aggregate:
                self.incoming_data[feed].append(data)
                # print("Message from {}: {}".format(feed, data))

        self.agent.subscribe(handler, feed)
        self.incoming_data[feed] =[]
        self.log.info("Subscribed to feed {}".format(feed))

        return True, 'Subscribed to data feeds.'

    def write_data_to_file(self):

        for feed_name, data_list in self.incoming_data.items():
            if len(data_list) == 0:
                continue

            # Creates frame from datastream
            frame = core.G3Frame(core.G3FrameType.Housekeeping)

            frame["agent_address"] = data_list[0]["agent_address"]
            frame["session_id"] = data_list[0]["session_id"]

            tods = {}
            timestamps = {}

            # Creats tods and timestamps from frame data
            for data_point in data_list:
                for key, val in data_point["data"].items():
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

            self.file(frame)

            # clear data feed
            self.incoming_data[feed_name] = []

    def start_file(self):
        print("Creating file: {}".format(self.filename))
        self.file = core.G3Writer(filename=self.filename)
        return

    def end_file(self):
        self.write_data_to_file()
        self.file(core.G3Frame(core.G3FrameType.EndProcessing))

        print("Closing file: {}".format(self.filename))

        return

    def start_aggregate(self, session, params={}):
        session.post_status('running')

        new_file_time = True
        new_frame_time = True

        time_per_frame = 60 * 10 # [s]
        time_per_file  = 60 * 60  # [s]
        self.aggregate = True
        while self.aggregate:

            if new_file_time:
                if self.file is not None:
                    self.end_file()

                file_start_time = time.time()
                time_string = time.strftime("%Y-%m-%d_T_%H:%M:%S", time.localtime(file_start_time))
                self.filename = "data/{}.g3".format(time_string)
                self.start_file()

                session.post_message('Starting a new DAQ file: %s' % self.filename)

                new_file_time = False

            if new_frame_time:
                self.write_data_to_file()
                new_frame_time = False
                frame_start_time = time.time()

            time.sleep(.1)
            # Check if its time to write new frame/file
            new_file_time = (time.time() - file_start_time) > time_per_file
            new_frame_time = (time.time() - frame_start_time) > time_per_frame

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

    agent.register_task('subscribe', data_aggregator.subscribe_to_feed)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
