from ocs import ocs_agent, site_config, client_t, ocs_feed
import time
import threading
import os
import txaio

from os import environ
import numpy as np
from autobahn.wamp.exception import ApplicationError
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()

class FakeDataAgent:
    def __init__(self, agent,
                 num_channels=2,
                 sample_rate=10.,
                 frame_length=60):
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()
        self.job = None
        self.channel_names = ['channel_%02i' % i for i in range(num_channels)]
        self.sample_rate = max(1e-6, sample_rate) # #nozeros

        # Register feed
        agg_params = {
            'frame_length': frame_length
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

        The most recent fake values are stored in the session.data object in
        the format::

            {"fields":
                {"channel_00": 0.10250430068515494,
                 "channel_01": 0.08550903376216404,
                 "channel_02": 0.10481891991693446,
                 "channel_03": 0.10793263271024509},
             "timestamp":1600448753.9288929}

        The channels kept in fields are the 'faked' data, in a similar
        structure to the Lakeshore agents. 'timestamp' is the lastest time these values
        were updated.

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

            # Update session.data
            data_cache = {"fields": {}, "timestamp": None}
            for channel, samples in block.data.items():
                data_cache['fields'][channel] = samples[-1]
            data_cache['timestamp'] = block.timestamps[-1]
            session.data.update(data_cache)

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

    # Tasks
    
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

    @inlineCallbacks
    def delay_task(self, session, params={}):
        """Task that will take the requested number of seconds to complete.

        This can run simultaneously with the acq Process.  This Task
        should run in the reactor thread.

        The session data will be updated with the requested delay as
        well as the time elapsed so far, for example::

            {'requested_delay': 5.,
             'delay_so_far': 1.2}

        Args:
            delay (float): Time to wait before returning, in seconds.
                Defaults to 5.
            succeed (bool): Whether to return success or not.
                Defaults to True.

        """
        session.set_status('running')
        delay = params.get('delay', 5)
        session.data = {'requested_delay': delay,
                        'delay_so_far': 0}
        succeed = params.get('succeed', True) is True
        t0 = time.time()
        while True:
            session.data['delay_so_far'] = time.time() - t0
            sleep_time = min(0.5, delay - session.data['delay_so_far'])
            if sleep_time < 0:
                break
            yield dsleep(sleep_time)
        return succeed, 'Exited after %.1f seconds' % session.data['delay_so_far']


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
    pgroup.add_argument('--frame-length', default=60, type=int,
                        help='Frame length to pass to the aggregator parameters.')

    return parser_in

if __name__ == '__main__':
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = add_agent_args()
    args = site_config.parse_args(agent_class='FakeDataAgent', parser=parser)

    startup = False
    if args.mode == 'acq':
        startup=True
    
    agent, runner = ocs_agent.init_site_agent(args)

    fdata = FakeDataAgent(agent,
                          num_channels=args.num_channels,
                          sample_rate=args.sample_rate,
                          frame_length=args.frame_length)
    agent.register_process('acq', fdata.start_acq, fdata.stop_acq,
                           blocking=True, startup=startup)
    agent.register_task('set_heartbeat', fdata.set_heartbeat_state)
    agent.register_task('delay_task', fdata.delay_task, blocking=False)

    runner.run(agent, auto_reconnect=True)
