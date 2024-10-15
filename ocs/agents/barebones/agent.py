import time
import txaio

from os import environ

from ocs import ocs_agent, site_config
from ocs.ocs_twisted import TimeoutLock


class BarebonesAgent:
    """Barebone Agent demonstrating writing an Agent from scratch.

    This Agent is meant to be an example for Agent development, and provides a
    clean starting point when developing a new Agent.

    Parameters:
        agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.

    Attributes:
        agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.
        log (txaio.tx.Logger): Logger object used to log events within the
            Agent.
        lock (TimeoutLock): TimeoutLock object used to prevent simultaneous
            commands being sent to hardware.
        _count (bool): Internal tracking of whether the Agent should be
            counting or not. This is used to exit the Process loop by changing
            it to False via the count.stop() command. Your Agent won't use this
            exact attribute, but might have a similar one.

    """

    def __init__(self, agent):
        self.agent = agent
        self.log = agent.log
        self.lock = TimeoutLock(default_timeout=5)
        self._count = False

        # Register OCS feed
        agg_params = {
            'frame_length': 10 * 60  # [sec]
        }
        self.agent.register_feed('feed_name',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=1.)

    def count(self, session, params):
        """count(test_mode=False)

        **Process** - Count up from 0.

        The count will restart if the process is stopped and restarted.

        Notes:
            The most recent value is stored in the session data object in the
            format::

                >>> response.session['data']
                {"value": 0,
                 "timestamp":1600448753.9288929}

        """
        with self.lock.acquire_timeout(timeout=0, job='count') as acquired:
            if not acquired:
                print("Lock could not be acquired because it "
                      + f"is held by {self.lock.job}")
                return False

            # Initialize last release time for lock
            last_release = time.time()

            # Initialize the counter
            self._count = True
            counter = 0

            self.log.info("Starting the count!")

            # Main process loop
            while self._count:
                # About every second, release and acquire the lock
                if time.time() - last_release > 1.:
                    last_release = time.time()
                    if not self.lock.release_and_acquire(timeout=10):
                        print(f"Could not re-acquire lock now held by {self.lock.job}.")
                        return False

                # Perform the process actions
                counter += 1
                self.log.debug(f"{counter}! Ah! Ah! Ah!")
                now = time.time()
                session.data = {"value": counter,
                                "timestamp": now}

                # Format message for publishing to Feed
                message = {'block_name': 'count',
                           'timestamp': now,
                           'data': {'value': counter}}
                self.agent.publish_to_feed('feed_name', message)
                time.sleep(1)

        self.agent.feeds['feed_name'].flush_buffer()

        return True, 'Acquisition exited cleanly.'

    def _stop_count(self, session, params):
        """Stop monitoring the turbo output."""
        if self._count:
            self._count = False
            return True, 'requested to stop taking data.'
        else:
            return False, 'count is not currently running'

    @ocs_agent.param('text', default='hello world', type=str)
    def print(self, session, params):
        """print(text='hello world')

        **Task** - Print some text passed to a Task.

        Args:
            text (str): Text to print out. Defaults to 'hello world'.

        Notes:
            The session data will be updated with the text::

                >>> response.session['data']
                {'text': 'hello world',
                 'last_updated': 1660249321.8729222}

        """
        with self.lock.acquire_timeout(timeout=3.0, job='print') as acquired:
            if not acquired:
                self.log.warn("Lock could not be acquired because it "
                              + f"is held by {self.lock.job}")
                return False

            # Log the text provided to the Agent logs
            self.log.info(f"{params['text']}")

            # Store the text provided in session.data
            session.data = {'text': params['text'],
                            'last_updated': time.time()}

        # bool, 'descriptive text message'
        # True if task succeeds, False if not
        return True, 'Printed text to logs'


def add_agent_args(parser_in=None):
    if parser_in is None:
        from argparse import ArgumentParser as A
        parser_in = A()
    pgroup = parser_in.add_argument_group('Agent Options')
    pgroup.add_argument('--mode', type=str, default='count',
                        choices=['idle', 'count'],
                        help="Starting action for the Agent.")

    return parser_in


def main(args=None):
    # For logging
    txaio.use_twisted()
    txaio.make_logger()

    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = add_agent_args()
    args = site_config.parse_args(agent_class='BarebonesAgent',
                                  parser=parser,
                                  args=args)

    startup = False
    if args.mode == 'count':
        startup = True

    agent, runner = ocs_agent.init_site_agent(args)

    barebone = BarebonesAgent(agent)
    agent.register_process(
        'count',
        barebone.count,
        barebone._stop_count,
        startup=startup)
    agent.register_task('print', barebone.print)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
