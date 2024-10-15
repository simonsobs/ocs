import time
import queue
import argparse
import txaio

from os import environ

from ocs import ocs_agent, site_config
from ocs.base import OpCode

from ocs.agents.influxdb_publisher.drivers import Publisher

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


class InfluxDBAgent:
    """
    This class provide a WAMP wrapper for the data publisher. The run function
    and the data handler **are** thread-safe, as long as multiple run functions
    are not started at the same time, which should be prevented through
    OCSAgent.

    Args:
        agent (OCSAgent):
            OCS Agent object
        args (namespace):
            args from the function's argparser.

    Attributes:
        data_dir (path):
            Path to the base directory where data should be written.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        incoming_data (queue.Queue):
            Thread-safe queue where incoming (data, feed) pairs are stored
            before being passed to the Publisher.
        loop_time (float):
            Time between iterations of the run loop.
    """

    def __init__(self, agent, args):
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log
        self.args = args

        self.aggregate = False
        self.incoming_data = queue.Queue()
        self.loop_time = 1

        self.agent.subscribe_on_start(self._enqueue_incoming_data,
                                      f'{args.address_root}..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record',
                                    self.record, self._stop_record,
                                    startup=record_on_start)

    def _enqueue_incoming_data(self, _data):
        """Data handler for all feeds. This checks to see if the feeds should
        be recorded, and if they are it puts them into the incoming_data queue
        to be processed by the Publisher during the next run iteration.

        """
        data, feed = _data

        if not feed['record'] or not self.aggregate:
            return

        # LOG.debug("data: {d}", d=data)
        # LOG.debug("feed: {f}", f=feed)

        self.incoming_data.put((data, feed))

    @ocs_agent.param('test_mode', default=False, type=bool)
    def record(self, session: ocs_agent.OpSession, params):
        """record()

        **Process** - This process will create an Publisher instance, which
        will collect and write provider data to disk as long as this process is
        running.

        Parameters:
            test_mode (bool, optional): Run the record Process loop only once.
                This is meant only for testing. Default is False.

        """
        self.aggregate = True

        self.log.debug("Instatiating Publisher class")
        publisher = Publisher(self.args.host,
                              self.args.database,
                              self.incoming_data,
                              port=self.args.port,
                              protocol=self.args.protocol,
                              gzip=self.args.gzip,
                              operate_callback=lambda: self.aggregate,
                              )

        while self.aggregate:
            time.sleep(self.loop_time)
            self.log.debug(f"Approx. queue size: {self.incoming_data.qsize()}")
            publisher.run()

            if params['test_mode']:
                break

        publisher.close()

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
    pgroup.add_argument('--initial-state',
                        default='record', choices=['idle', 'record'],
                        help="Initial state of argument parser. Can be either "
                             "idle or record")
    pgroup.add_argument('--host',
                        default='influxdb',
                        help="InfluxDB host address.")
    pgroup.add_argument('--port',
                        default=8086,
                        help="InfluxDB port.")
    pgroup.add_argument('--database',
                        default='ocs_feeds',
                        help="Database within InfluxDB to publish data to.")
    pgroup.add_argument('--protocol',
                        default='line',
                        choices=['json', 'line'],
                        help="Protocol for writing data. Either 'line' or "
                             "'json'.")
    pgroup.add_argument('--gzip',
                        type=bool,
                        default=False,
                        help="Use gzip content encoding to compress requests.")

    return parser


def main(args=None):
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = make_parser()
    args = site_config.parse_args(agent_class='InfluxDBAgent',
                                  parser=parser,
                                  args=args)

    agent, runner = ocs_agent.init_site_agent(args)

    InfluxDBAgent(agent, args)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
