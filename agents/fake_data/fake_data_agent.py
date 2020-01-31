from ocs import ocs_agent, site_config, client_t, ocs_feed
import time
import threading
import os
from autobahn.wamp.exception import ApplicationError
import numpy as np

class FakeDataAgent:
    def __init__(self, agent,
                 num_channels=2,
                 sample_rate=10.):
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()
        self.job = None
        self.channel_names = ['channel_%02i' % i for i in range(num_channels)]
        self.sample_rate = max(1e-6, sample_rate) # #nozeros

        # Register feed
        agg_params = {
            'frame_length': 60
        }
        print('registering')
        self.agent.register_feed('false_temperatures',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=0.)

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
        """**Process:**  Acquire data and write to the feed.

        This Process has no useful parameters.

        """
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.set_status('running')

        if params is None:
            params = {}

        T = [.100 for c in self.channel_names]
        block = ocs_feed.Block('temps', self.channel_names)

        next_timestamp = time.time()
        reporting_interval = 1.
        next_report = next_timestamp + reporting_interval

        self.log.info("Starting acquisition")

        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10

            now = time.time()
            delay_time = next_report - now
            if delay_time > 0:
                time.sleep(min(delay_time, 1.))
                continue

            # Safety: if we ever get waaaay behind, reset.
            if delay_time / reporting_interval < -3:
                self.log.info('Got way behind in reporting: %.1s seconds. '
                              'Dropping fake data.' % delay_time)
                next_timestamp = now
                next_report = next_timestamp + reporting_interval
                continue

            # Pretend we got it exactly.
            n_data = int((next_report - next_timestamp) * self.sample_rate)

            # Set the next report time, before checking n_data.
            next_report += reporting_interval

            # This is to handle the (acceptable) case of sample_rate < 0.
            if (n_data <= 0):
                time.sleep(.1)
                continue

            # New data bundle.
            t = next_timestamp + np.arange(n_data) / self.sample_rate
            block.timestamps = list(t)

            # Unnecessary realism: 1/f.
            T = [_t + np.random.uniform(-1, 1) * .003 for _t in T]
            for _t, _c in zip(T, self.channel_names):
                block.data[_c] = list(_t + np.random.uniform(
                    -1, 1, size=len(t)) * .002)

            # This will keep good fractional time.
            next_timestamp += n_data / self.sample_rate

            # self.log.info('Sending %i data on %i channels.' % (len(t), len(T)))
            session.app.publish_to_feed('false_temperatures', block.encoded())

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

    def set_heartbeat_state(self, session, params=None):
        """Task to set the state of the agent heartbeat.

        Args:
            heartbeat (bool): True for on, False for off

        """
        # Default to on, which is what we generally want to be true
        heartbeat_state = params.get('heartbeat', True)

        self.agent._heartbeat_on = heartbeat_state
        self.log.info("Setting heartbeat_on: {}...".format(heartbeat_state))

        return True, "Set heartbeat_on: {}".format(heartbeat_state)



def add_agent_args(parser_in=None):
    if parser_in is None:
        from argparse import ArgumentParser as A
        parser_in = A()
    pgroup = parser_in.add_argument_group('Agent Options')
    pgroup.add_argument("--mode", default="idle", choices=['idle', 'acq'])
    pgroup.add_argument('--num-channels', default=2, type=int,
                        help='Number of fake readout channels to produce. '
                        'Channels are co-sampled.')
    pgroup.add_argument('--sample-rate', default=9.5, type=float,
                        help='Frequency at which to produce data.')

    return parser_in

if __name__ == '__main__':
    parser = add_agent_args()
    args = site_config.parse_args(agent_class='FakeDataAgent', parser=parser)

    startup = False
    if args.mode == 'acq':
        startup=True
    
    agent, runner = ocs_agent.init_site_agent(args)

    fdata = FakeDataAgent(agent,
                          num_channels=args.num_channels,
                          sample_rate=args.sample_rate)
    agent.register_process('acq', fdata.start_acq, fdata.stop_acq,
                           blocking=True, startup=startup)
    agent.register_task('set_heartbeat', fdata.set_heartbeat_state)

    runner.run(agent, auto_reconnect=True)
