from ocs import ocs_agent, site_config, client_t
import random
import time
import threading
import os
from autobahn.wamp.exception import ApplicationError


class FakeDataAgent:
    def __init__(self, agent,
                 num_channels=2):
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()
        self.job = None
        self.channel_names = ['channel_%02i' % i for i in range(num_channels)]

        # Register feed
        agg_params = {
            'blocking': {
                'temps': {'data': self.channel_names}
            }
        }
        print('registering')
        self.agent.register_feed('false_temperatures',
                                 record=True,
                                 agg_params=agg_params,
                                 buffered=True, buffer_time=10)


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
        """Start data acquisition.

        Args:
            params (dict): params dictionary with keys:
                'sampling_frequency' (float): sampling frequency for data collection
                                              defaults to 2.5 Hz

        """
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.set_status('running')

        if params is None:
            params = {}
        f_sample = params.get('sampling_frequency', 2.5)
        sleep_time = max(.01, 1./f_sample)

        T = [.100 for c in self.channel_names]

        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10

            data = {
                'timestamp': time.time(),
                'block_name': 'temps',
                'data': {}
            }
            T = [_t + random.uniform(-1, 1) * .003 for _t in T]
            for _t, _c in zip(T, self.channel_names):
                data['data'][_c] = _t

            time.sleep(sleep_time)
            session.app.publish_to_feed('false_temperatures', data)

        self.agent.feeds['false_temperatures'].flush_buffer()
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
    parser = site_config.add_arguments()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--num-channels', default=2, type=int)

    # Parse comand line.
    args = parser.parse_args()

    # Interpret options in the context of site_config.
    site_config.reparse_args(args, 'FakeDataAgent')
    
    agent, runner = ocs_agent.init_site_agent(args)

    fdata = FakeDataAgent(agent, num_channels=args.num_channels)
    agent.register_process('acq', fdata.start_acq, fdata.stop_acq,
                           blocking=True)

    runner.run(agent, auto_reconnect=True)
