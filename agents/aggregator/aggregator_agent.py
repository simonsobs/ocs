import time, threading
import numpy as np
from ocs import ocs_agent
from spt3g import core
# import op_model as opm


class DataAggregator:

    def __init__(self, agent):

        self.lock = threading.Semaphore()
        self.job = None
        self.agent = agent

        self.incoming_data = {}

        # TODO(Jack): List of feeds should be obtained dynamically
        self.feeds = [u'observatory.thermometry']
        self.filename = ""
        self.file = None

    # Exclusive access management.
    
    def try_set_job(self, job_name):
        with self.lock:
            if self.job is None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    def handler(self, data):
        """
        Handles data published to feed.
        """
        # Do we want to save data before aggregate starts? Probably doesn't matter
        if self.job == 'aggregate':
            subscriber_address = data["agent_address"]
            self.incoming_data[subscriber_address].append(data)
            #print ("Message from %s: got value %s "% (subscriber_address, data))

    # Task to subscribe to data feeds
    def subscribe_to_topics(self, sessions, params=None):
        ok, msg = self.try_set_job('subscribe')
        if not ok:
            return ok, msg

        # try:
        #     self.feeds = params["feeds"]
        # except ValueError:
        #     print("feeds not specified")

        for feed in self.feeds:
            self.agent.subscribe(self.handler, feed + '.data')
            print("Subscribed to feed: {}".format(feed))
            self.incoming_data[feed] = []

        self.set_job_done()
        return True, 'Subscribed to data feeds.'

    def write_data_to_file(self):
        for feed in self.feeds:
            if len(self.incoming_data[feed]) == 0:
                continue

            # Creates frame from datastream

            frame = core.G3Frame(core.G3FrameType.Housekeeping)
            frame_data = self.incoming_data[feed]

            frame["agent_address"] = frame_data[0]["agent_address"]
            frame["session_id"] = frame_data[0]["session_id"]
            print(frame_data[0])

            tods = {}
            timestamps = {}

            # Creats tods and timestamps from frame data
            for data_point in frame_data:
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
            self.incoming_data[feed] = []

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
        ok, msg = self.try_set_job('aggregate')
        if not ok: return ok, msg
        session.post_status('running')

        new_file_time = True
        new_frame_time = True

        time_per_frame = 60 * 10 # [s]
        time_per_file  = 60 * 60  # [s]

        while True:
            with self.lock:
                if self.job == '!aggregate':
                    break
                elif self.job == 'aggregate':
                    pass
                else:
                    return 10

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
        self.set_job_done()
        return True, 'Acquisition exited cleanly.'
            
    def stop_aggregate(self, session, params=None):
        ok = False
        with self.lock:
            if self.job =='aggregate':
                self.job = '!aggregate'
                ok = True

        return (ok, {True: 'Requested process stop.',
                     False: 'Failed to request process stop.'}[ok])


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent(u'observatory.data_aggregator')

    data_aggregator = DataAggregator(agent)

    agent.register_task('subscribe', data_aggregator.subscribe_to_topics)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
