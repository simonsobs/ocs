from ocs import ocs_agent
from ocs.Lakeshore.Lakeshore372 import LS372
import random
import time, threading

class Thermo372:
    """
        Agent to connect to a single Lakeshore 372 device.
        
        Params:
            agent: Application Session
            ip:  ip address of agent 
            fake_data: generates random numbers without connecting to LS if True. 
    """
    def __init__(self, agent, ip, fake_data=False):
        self.agent = agent
        self.lock = threading.Semaphore()
        self.job = None

        self.ip = ip
        self.fake_data = fake_data
        self.module = None

    def try_set_job(self, job_name):
        with self.lock:
            if self.job == None:
                self.job = job_name
                return True, 'ok'
            else:
                return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    def init_lakeshore_task(self, session, params=None):
        ok, msg = self.try_set_job('init')

        print('Initialize Lakeshore:', ok)
        if not ok:
            return ok, msg

        session.post_status('starting')

        if self.fake_data:
            session.post_message("No initialization since faking data")
        else:
            self.module = LS372(self.ip)

        self.set_job_done()
        return True, 'Lakeshore module initialized.'

    def start_acq(self, session, params=None):
        ok, msg = self.try_set_job('acq')
        if not ok:
             return ok, msg
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
                time.sleep(.1)
            else:
                reading = self.module.get_temp(unit='S')
                time.sleep(.01)

            print("Reading: ", reading)
            session.post_data(reading)

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
    
    import json
    ip_filename = "/home/so_user/so/ocs/ocs/Lakeshore/ips.json"
    with open(ip_filename) as file:
        ips = json.load(file)

    therm = Thermo372(agent, ips["LS372A"] , fake_data=False)

    agent.register_task('lakeshore', therm.init_lakeshore_task)
    agent.register_process('acq', therm.start_acq, therm.stop_acq)

    runner.run(agent, auto_reconnect=True)

