from ocs import ocs_agent
from Lakeshore240 import Module
import random
#import op_model as opm

import time, threading

class Thermometry:

    def __init__(self, agent, fake_data = False):
        self.agent = agent
        self.lock = threading.Semaphore()
        self.job = None
        self.fake_data = fake_data
        self.module = None

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
    
    def init_lakeshore_task(self, session, params=None):
        ok, msg = self.try_set_job('init')
        
        print('Initialize Lakeshore:', ok)
        if not ok:
            return ok, msg
        
        session.post_status('starting')    
        
        if self.fake_data:
            session.post_message("No initialization since faking data")
        else:
            try: 
                self.module = Module()
                session.post_message("Lakeshore initialized with ID: %s"%self.module.idn)
            except Exception as e:
                print(e)

        
        self.set_job_done()
        return True, 'Lakeshore module initialized.'
        
    
    def upload_calibration_curve_task(self, session, params=None):
        pass
    

    # Process functions.    
    
    def start_acq(self, session, params=None):
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.post_status('running')
    
    
        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10
            
            if self.fake_data:
                reading = random.randrange(250, 350)
                time.sleep(.5)
            else:
                reading = self.module.channels[0].getReading()
            
            print ("Reading: ", reading)
            
            session.post_message(reading)


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
    agent, runner = ocs_agent.init_ocs_agent('observatory.thermometry')

    therm = Thermometry(agent, fake_data = True)
    
    agent.register_task('lakeshore', therm.init_lakeshore_task)
    agent.register_process('acq', therm.start_acq, therm.stop_acq)

    runner.run(agent, auto_reconnect=True)
