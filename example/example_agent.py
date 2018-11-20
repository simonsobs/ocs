from ocs import ocs_agent
#import op_model as opm

import time, threading

class MyHardwareDevice:

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

    # Task functions.

    def squids_task(self, session, params=None):
        ok, msg = self.try_set_job('squids')
        print('start squids:', ok)
        if not ok:
            return ok, msg
        session.set_status('running')

        for step in range(5):
            session.add_message('Tuning step %i' % step)
            time.sleep(1)

        self.set_job_done()
        return True, 'Squid tune complete.'

    def dets_task(self, session, params=None):
        ok, msg = self.try_set_job('dets')
        print('start dets:', ok)
        if not ok: return ok, msg
        session.set_status('running')

        for i in range(5):
            session.add_message('Dets still tasking...')
            time.sleep(1)

        self.set_job_done()
        return True, 'Det bias complete.'

    # Process functions.

    def start_acq(self, session, params=None):
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.set_status('running')

        n_frames = 0
        while True:
            with self.lock:
                print('Checking...', self.job)
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10
            n_frames += 100
            time.sleep(.5)
            session.add_message('Acquired %i frames...' % n_frames)

        self.set_job_done()
        return True, 'Acquisition exited cleanly.'
            
    def stop_acq(self, session, params=None):
        ok = False
        with self.lock:
            if self.job =='acq':
                self.job = '!acq'
                ok = True
        return (ok, {True: 'Requested process stop.',
                    False: 'Failed to request process stop.'}[ok])


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.dets1')

    my_hd = MyHardwareDevice()
    agent.register_task('squids', my_hd.squids_task) 
    agent.register_task('dets', my_hd.dets_task) 
    agent.register_process('acq', my_hd.start_acq, my_hd.stop_acq)

    runner.run(agent, auto_reconnect=True)
