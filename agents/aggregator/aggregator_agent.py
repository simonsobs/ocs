import time, threading

from ocs import ocs_agent
# from spt3g import core
#import op_model as opm


class DataAggregator:

    def __init__(self, agent):
        self.lock = threading.Semaphore()
        self.job = None
        self.agent = agent

        self.incoming_data = {}
        self.feeds = [u'observatory.thermometry']
        self.filename = ""

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

    # Task to subscribe to data feeds
    def subscribe_to_topics(self, sessions, parmams=None):
        ok, msg = self.try_set_job('subscribe')
        
        if not ok:
            return ok, msg

        for feed in self.feeds:
            print ()

            self.agent.subscribe(self.handler, feed + u'.data')
            print ("Subscribed to feed: %s" % (feed + '.data'))
            self.incoming_data[feed] = []

        self.set_job_done()
        return True, 'Lakeshore module initialized.'



    def write_data_to_file(self):
        for feed in self.feeds:
            frame = self.make_frame_from_data(feed)
            # core.G3Writer(frame, filename = ("%d.g3" % self.filename))
            self.incoming_data[feed] = []


    def end_file(self):
        #TODO (Jack/Joy) Save all remaining data to disk and write endframe
        self.write_data_to_file()
        # core.G3Writer(core.G3Frame(core.G3FrameType.EndProcessing)) 
        pass

    def start_file(self):
        #TODO (Jack/Joy) Create new file and initialize it
        pass


    def make_frame_from_data(self, topic):
        print ("NOT IMPLEMENTED")
        data = [e["channel"] for e in self.incoming_data[topic]]
        print ("Making frame from data: %s"%data)
        return data

        frame = core.G3Frame(core.G3FrameType.Housekeeping)
        data = self.incoming_data[topic]
        frame["agent_address"] = data["agent_address"][0]
        frame["session_id"] = data["session_id"][0]
        # tsm = core.G3TimestreamMap()
        ts = [element["channel"][1] for element in data]
        ts = np.array(ts)
        ts = core.G3Timestream(ts)
        ts.start = data[0]["channel"][0]
        ts.stop = data[-1]["channel"][0]
        # TODO (Jack/Joy): pass the units through the feed
        ts.units = core.G3TimestreamUnits.K
        # TODO (Jack/Joy): there will be more channel names and prob G3TimestreamMap
        # frame["tempertures"] = tsm
        frame["channel"] = ts
        return frame

    def handler(self, data):
        # Do we want to save data before aggregate starts? Probably doesn't matter
        if self.job == 'aggregate':
            subscriber_address = data["agent_address"]
            self.incoming_data[subscriber_address].append(data)
            print ("Message from %s: got value %s "% (subscriber_address, data))




    def start_aggregate(self, session, params=None):
        ok, msg = self.try_set_job('aggregate')
        if not ok: return ok, msg
        session.post_status('running')

        new_file_time = False
        new_frame_time = False

        file_start_time = time.time()
        frame_start_time = time.time()

        self.filename = frame_start_time
        self.start_file()


        # TODO(): List of feeds should be obtained dynamically

        while True:
            with self.lock:
                if self.job == '!aggregate':
                    break
                elif self.job == 'aggregate':
                    pass
                else:
                    return 10
            
            if new_frame_time:
                self.write_data_to_file()
                new_frame_time = False
                frame_start_time = time.time()

            if new_file_time:

                self.end_file()

                file_start_time = time.time()
                self.filename = file_start_time

                self.start_file()

                session.post_message('Starting a new DAQ file: %s' % self.filename)
                
                new_file_time = False

            #Check if its time to write new frame/file
            time.sleep(.1)
            #Might want to use core.G3Units.s and core.G3Units.min here...
            file_dt = (time.time() - file_start_time)
            frame_dt = (time.time() - frame_start_time)


            if file_dt > (15 * 60): 
                new_file_time = True
            if frame_dt > (10):
                new_frame_time = True
            
        self.set_job_done()
        return True, 'Acquisition exited cleanly.'
            
    def stop_aggregate(self, session, params=None):
        ok = False
        with self.lock:
            if self.job =='aggregate':
                self.job = '!aggregate'
                ok = True

        self.end_file()

        return (ok, {True: 'Requested process stop.',
                    False: 'Failed to request process stop.'}[ok])


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent(u'observatory.data_aggregator')

    data_aggregator = DataAggregator(agent)

    agent.register_task('subscribe', data_aggregator.subscribe_to_topics)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
