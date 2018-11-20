from ocs import ocs_agent, site_config
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
    # Get the default ocs argument parser.
    parser = site_config.add_arguments()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--serial-number')
    pgroup.add_argument('--mode')
    
    # Parse comand line.
    args = parser.parse_args()

    # Interpret options in the context of site_config.
    site_config.reparse_args(args, 'Riverbank320Agent')
    print('I am in charge of device with serial number: %s' % args.serial_number)

    agent, runner = ocs_agent.init_site_agent(args)

    my_hd = MyHardwareDevice()
    agent.register_process('acq', my_hd.start_acq, my_hd.stop_acq)

    runner.run(agent, auto_reconnect=True)
