import time, threading

from ocs import ocs_agent
from spt3g import core
#import op_model as opm


class DataAggregator:

    def __init__(self, agent):
        self.lock = threading.Semaphore()
        self.job = None
        self.agent = agent

    # Exclusive access management.
    
    def try_set_job(self, job_name):
        with self.lock:
            if self.job == None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    def get_data(self, topic):
        frame = core.G3Frame(core.G3FrameType.Housekeeping)
        data = {"sensor1": np.arange(100), "sensor2": np.arange(100, 200)}
        # tsm = core.G3TimestreamMap()
        for key in data.keys():
            ts = core.G3Timestream(data[key])
            ts.start = 0
            ts.stop = 100
            ts.units = core.G3TimestreamUnits.K
            # tsm[ts] = ts
            frame[key] = ts
        # frame["tempertures"] = tsm
        if len(frame.keys()) > 0:
            return frame
        else:
            return None

    def handler(self, data):
        subscriber_address = data["agent_address"]
        self.incoming_data[subscriber_address].append(data)
        print ("Message from %s: got value %f "%subscirber_address, data["channel"])

    # Task functions.

    # Process functions.

    def start_aggregate(self, session, params=None):
        ok, msg = self.try_set_job('aggregate')
        if not ok: return ok, msg
        session.post_status('running')


        new_file_time = True
        new_frame_time = False
        filename = time.time()
        file_start_time = filename
        frame_start_time = time.time()

        # TODO(): List of feeds should be obtained dynamically
        self.incoming_data = {}
        feeds = [u'observatory.thermometry.data'] 
        for feed in feeds:
            yield self.agent.subscribe(self.handler, feed)
            print("Subscribed to feed: %s" % feed)
            self.incoming_data[feed[:-5]] = []

        while True:
            with self.lock:
                print('Checking...', self.job)
                if self.job == '!aggregate':
                    break
                elif self.job == 'aggregate':
                    pass
                else:
                    return 10
            if new_file_time:
                filename = time.time()
                session.post_message('Starting a new DAQ file: %s' % filename)
                file_start_time = filename
                # TODO(Jack/Joy): Add stuff that you write in each new file
                new_file_time = False
            if new_frame_time:
                for feed in feeds:
                    frame = self.make_frame_from_data(self.incoming_data[feed[:-5]])
                    core.G3Writer(frame, filename = ("%d.g3" % filename))
                    session.post_message('Wrote a frames for feed' % feed)
                new_frame_time = False
                frame_start_time = time.time()
            time.usleep(100)
            file_dt = (time.time() - file_start_time)*core.G3Units.s
            frame_dt = (time.time() - frame_start_time)*core.G3Units.s
            if file_dt > (15*core.G3Units.min):
                new_file_time = True
                core.G3Writer(core.G3Frame(core.G3FrameType.EndProcessing))
            if frame_dt > (10*core.G3Units.s):
                new_frame_time = True
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
    agent, runner = ocs_agent.init_ocs_agent('observatory.data_aggregator')

    data_aggregator = DataAggregator(agent)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
