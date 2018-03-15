from ocs import ocs_agent
#import op_model as opm

import time, threading

class DataAggregator:

    def __init__(self):
        self.lock = threading.Semaphore()
        self.job = None

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
        return np.arange(100)

    def modify_frame(self, frame):
        pass

    # Task functions.

    # Process functions.

    def start_aggregate(self, session, params=None):
        ok, msg = self.try_set_job('aggregate')
        if not ok: return ok, msg
        session.post_status('running')

        from spt3g import core
        #pipe = core.G3Pipeline()

        n_frames = 0
        topics = ["thermometry"] # list of topics should be taken from crossbar
        while True:
            with self.lock:
                print('Checking...', self.job)
                if self.job == '!aggregate':
                    break
                elif self.job == 'aggregate':
                    pass
                else:
                    return 10
            for topic in topics:
                data = self.get_data(topic)
                n_frames += 1 
                #pipe.Add(modify_frame)
                self.modify_frame(frame)
                core.G3Writer("dump.g3")
            #pipe.Add(core.G3Writer, filename="dump.g3")
            #pipe.Run()
            time.sleep(.5)
            session.post_message('Acquired %i frames...' % n_frames)

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

    data_aggregator = DataAggregator()
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
