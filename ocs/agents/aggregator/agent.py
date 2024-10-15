import time
import queue
import argparse
import txaio

from twisted.internet import reactor

from os import environ
from ocs import ocs_agent, site_config
from ocs.base import OpCode

from ocs.agents.aggregator.drivers import Aggregator

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


class AggregatorAgent:
    """
    This class provide a WAMP wrapper for the data aggregator. The run function
    and the data handler **are** thread-safe, as long as multiple run functions
    are not started at the same time, which should be prevented through OCSAgent.

    Args:
        agent (OCSAgent):
            OCS Agent object
        args (namespace):
            args from the function's argparser.

    Attributes:
        time_per_file (int):
            Time (sec) before files should be rotated.
        data_dir (path):
            Path to the base directory where data should be written.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        incoming_data (queue.Queue):
            Thread-safe queue where incoming (data, feed) pairs are stored before
            being passed to the Aggregator.
        loop_time (float):
            Time between iterations of the run loop.
    """

    def __init__(self, agent, args):
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log

        self.time_per_file = int(args.time_per_file)
        self.data_dir = args.data_dir

        self.aggregate = False
        self.incoming_data = queue.Queue()
        self.loop_time = 1

        # SUBSCRIBES TO ALL FEEDS!!!!
        # If this ends up being too much data, we can add a tag '.record'
        # at the end of the address of recorded feeds, and filter by that.
        self.agent.subscribe_on_start(self._enqueue_incoming_data,
                                      f'{args.address_root}..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record',
                                    self.record, self._stop_record,
                                    startup=record_on_start)

    def _enqueue_incoming_data(self, _data):
        """
        Data handler for all feeds. This checks to see if the feeds should
        be recorded, and if they are it puts them into the incoming_data queue
        to be processed by the Aggregator during the next run iteration.
        """
        data, feed = _data

        if not feed['record'] or not self.aggregate:
            return

        self.incoming_data.put((data, feed))
        self.log.debug("Enqueued {d} from Feed {f}", d=data, f=feed)

    @ocs_agent.param('test_mode', default=False, type=bool)
    def record(self, session: ocs_agent.OpSession, params):
        """record(test_mode=False)

        **Process** - This process will create an Aggregator instance, which
        will collect and write provider data to disk as long as this process is
        running.

        Parameters:
            test_mode (bool, optional): Run the record Process loop only once.
                This is meant only for testing. Default is False.

        Notes:
            The most recent file and active providers will be returned in the
            session data::

                >>> response.session['data']
                {"current_file": "/data/16020/1602089117.g3",
                 "providers": {
                    "observatory.fake-data1.feeds.false_temperatures": {
                        "last_refresh": 1602089118.8225083,
                        "sessid": "1602088928.8294137",
                        "stale": false,
                        "last_block_received": "temps"},
                    "observatory.LSSIM.feeds.temperatures": {
                         "last_refresh": 1602089118.8223345,
                         "sessid": "1602088932.335811",
                         "stale": false,
                         "last_block_received": "temps"}}}

        """
        self.aggregate = True

        try:
            aggregator = Aggregator(
                self.incoming_data,
                self.time_per_file,
                self.data_dir,
                session=session
            )
        except PermissionError:
            self.log.error("Unable to intialize Aggregator due to permission "
                           "error, stopping twisted reactor")
            reactor.callFromThread(reactor.stop)
            return False, "Aggregation not started"

        while self.aggregate:
            time.sleep(self.loop_time)
            aggregator.run()

            if params['test_mode']:
                break

        aggregator.close()

        return True, "Aggregation has ended"

    def _stop_record(self, session, params):
        if OpCode(session.op_code) in [OpCode.STARTING, OpCode.RUNNING]:
            session.set_status('stopping')
            self.aggregate = False
            return True, "Stopping aggregation"
        elif OpCode(session.op_code) == OpCode.STOPPING:
            return True, "record process status is already 'stopping'"
        else:
            return False, "record process not currently running"


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--data-dir', required=True,
                        help="Base directory to store data. "
                             "Subdirectories will be made here.")
    pgroup.add_argument('--initial-state',
                        default='idle', choices=['idle', 'record'],
                        help="Initial state of argument parser. Can be either"
                             "idle or record")
    pgroup.add_argument('--time-per-file', default='3600',
                        help="Time per file in seconds. Defaults to 1 hr")

    return parser


def main(args=None):
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = make_parser()
    args = site_config.parse_args(agent_class='AggregatorAgent',
                                  parser=parser,
                                  args=args)
    agent, runner = ocs_agent.init_site_agent(args)

    AggregatorAgent(agent, args)
    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
