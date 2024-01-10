from ocs import ocs_agent, site_config, ocs_feed
import time
import threading
import txaio

from os import environ
import numpy as np
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
        self.sample_rate = max(1e-6, sample_rate)  # nozeros

        # Register feed
        agg_params = {
            'frame_length': frame_length
        }
        print('registering')
        self.agent.register_feed('false_temperatures',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=1.)

    # Exclusive access management.
    def try_set_job(self, job_name):
        with self.lock:
            if self.job is None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    # Process functions.

    @ocs_agent.param('test_mode', default=False, type=bool)
    @ocs_agent.param('degradation_period', default=None, type=float)
    def acq(self, session, params):
        """acq(test_mode=False, degradation_period=None)

        **Process** - Acquire data and write to the feed.

        Parameters:
            test_mode (bool, optional): Run the acq Process loop only once.
                This is meant only for testing. Default is False.
            degradation_period (float, optional): If set, then
              alternately mark self as degraded / not degraded with
              this period (in seconds).

        Notes:
            The most recent fake values are stored in the session data object in
            the format::

                >>> response.session['data']
                {"fields":
                    {"channel_00": 0.10250430068515494,
                     "channel_01": 0.08550903376216404,
                     "channel_02": 0.10481891991693446,
                     "channel_03": 0.10793263271024509},
                 "timestamp":1600448753.9288929}

            The channels kept in fields are the 'faked' data, in a similar
            structure to the Lakeshore agents. 'timestamp' is the last time
            these values were updated.

        """
        ok, msg = self.try_set_job('acq')
        if not ok:
            return ok, msg

        T = [.100 for c in self.channel_names]
        block = ocs_feed.Block('temps', self.channel_names)

        next_timestamp = time.time()
        reporting_interval = 1.
        next_report = next_timestamp + reporting_interval

        next_deg_flip = None
        if params['degradation_period'] is not None:
            next_deg_flip = 0

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

            if next_deg_flip is not None and now > next_deg_flip:
                session.degraded = not session.degraded
                next_deg_flip = now + params['degradation_period']

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

            if params['test_mode']:
                break

        self.agent.feeds['false_temperatures'].flush_buffer()
        self.set_job_done()
        return True, 'Acquisition exited cleanly.'

    def _stop_acq(self, session, params):
        ok = False
        with self.lock:
            if self.job == 'acq':
                session.set_status('stopping')
                self.job = '!acq'
                ok = True
        return (ok, {True: 'Requested process stop.',
                     False: 'Failed to request process stop.'}[ok])

    @inlineCallbacks
    def count_seconds(self, session, params):
        # This process runs entirely in the reactor, as does its stop function.
        session.data = {'counter': 0,
                        'last_update': time.time()}
        while session.status == 'running':
            yield dsleep(1)
            session.data['last_update'] = time.time()
            session.data['counter'] += 1
        return True, 'Exited on request.'

    @inlineCallbacks
    def _stop_count_seconds(self, session, params):
        yield  # Make this a generator.
        session.set_status('stopping')

    # Tasks

    @ocs_agent.param('heartbeat', default=True, type=bool)
    def set_heartbeat(self, session, params):
        """set_heartbeat(heartbeat=True)

        **Task** -  Set the state of the agent heartbeat.

        Args:
            heartbeat (bool, optional): True for on (the default), False for off

        """
        heartbeat_state = params['heartbeat']

        self.agent._heartbeat_on = heartbeat_state
        self.log.info("Setting heartbeat_on: {}...".format(heartbeat_state))

        return True, "Set heartbeat_on: {}".format(heartbeat_state)

    @ocs_agent.param('delay', default=5., type=float, check=lambda x: x >= 0)
    @ocs_agent.param('succeed', default=True, type=bool)
    @inlineCallbacks
    def delay_task(self, session, params):
        """delay_task(delay=5, succeed=True)

        **Task** (abortable) - Sleep (delay) for the requested number of
        seconds.

        This can run simultaneously with the acq Process.  This Task
        should run in the reactor thread.

        Args:
            delay (float, optional): Time to wait before returning, in seconds.
                Defaults to 5.
            succeed (bool, optional): Whether to return success or not.
                Defaults to True.

        Notes:
            The session data will be updated with the requested delay as
            well as the time elapsed so far, for example::

                >>> response.session['data']
                {'requested_delay': 5.,
                 'delay_so_far': 1.2}

        """
        delay = params['delay']
        succeed = params['succeed'] is True

        session.data = {'requested_delay': delay,
                        'delay_so_far': 0}
        t0 = time.time()
        while session.status == 'running':
            session.data['delay_so_far'] = time.time() - t0
            sleep_time = min(0.5, delay - session.data['delay_so_far'])
            if sleep_time < 0:
                break
            yield dsleep(sleep_time)

        if session.status != 'running':
            return False, 'Aborted after %.1f seconds' % session.data['delay_so_far']

        return succeed, 'Exited after %.1f seconds' % session.data['delay_so_far']

    @inlineCallbacks
    def _abort_delay_task(self, session, params):
        if session.status == 'running':
            session.set_status('stopping')
        yield


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


def main(args=None):
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = add_agent_args()
    args = site_config.parse_args(agent_class='FakeDataAgent',
                                  parser=parser,
                                  args=args)

    startup = False
    if args.mode == 'acq':
        startup = True

    agent, runner = ocs_agent.init_site_agent(args)

    fdata = FakeDataAgent(agent,
                          num_channels=args.num_channels,
                          sample_rate=args.sample_rate,
                          frame_length=args.frame_length)
    agent.register_process('acq', fdata.acq, fdata._stop_acq,
                           blocking=True, startup=startup)
    agent.register_process('count', fdata.count_seconds, fdata._stop_count_seconds,
                           blocking=False, startup=startup)
    agent.register_task('set_heartbeat', fdata.set_heartbeat)
    agent.register_task('delay_task', fdata.delay_task, blocking=False,
                        aborter=fdata._abort_delay_task)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
