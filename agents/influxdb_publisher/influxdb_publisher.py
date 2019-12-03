import time
import datetime
import os
import queue
import argparse
import txaio

from os import environ
from influxdb import InfluxDBClient
from requests.exceptions import ConnectionError as RequestsConnectionError

from ocs import ocs_agent, site_config

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()

def timestamp2influxtime(time):
    """Convert timestamp for influx

    Args:
        time:
            ctime timestamp

    """
    t_dt = datetime.datetime.fromtimestamp(time)
    return t_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")

class Publisher:
    """
    Data publisher. This manages data to be published to the InfluxDB.

    This class should only be accessed by a single thread. Data can be passed
    to it by appending it to the referenced `incoming_data` queue.

    Args:
        incoming_data (queue.Queue):
            A thread-safe queue of (data, feed) pairs.
        host (str):
            host for InfluxDB instance.
        port (int, optional):
            port for InfluxDB instance, defaults to 8086.

    Attributes:
        host (str):
            host for InfluxDB instance.
        port (int, optional):
            port for InfluxDB instance, defaults to 8086.
        incoming_data:
            data to be published
        client:
            InfluxDB client connection

    """
    def __init__(self, host, incoming_data, port=8086):
        self.host = host
        self.port = port
        self.incoming_data = incoming_data

        self.client = InfluxDBClient(host=self.host, port=self.port)

        db_list = self.client.get_list_database()
        db_names = [x['name'] for x in db_list]
        
        if 'ocs_feeds' not in db_names:
            print("ocs_feeds DB doesn't exist, creating DB")
            self.client.create_database('ocs_feeds')
        
        self.client.switch_database('ocs_feeds')

    def process_incoming_data(self):
        """
        Takes all data from the incoming_data queue, and puts them into
        provider blocks.
        """
        while not self.incoming_data.empty():
            data, feed = self.incoming_data.get()

            LOG.debug("Pulling data from queue.")
            #LOG.debug("data: {d}", d=data)
            #LOG.debug("feed: {f}", f=feed)

            # Formatted for writing to InfluxDB
            payload = self.format_data(data, feed)
            try:
                self.client.write_points(payload)
                LOG.debug("wrote payload to influx")
            except RequestsConnectionError:
                LOG.error("InfluxDB unavailable, attempting to reconnect.")
                self.client = InfluxDBClient(host=self.host, port=self.port)
                self.client.switch_database('ocs_feeds')

    def format_data(self, data, feed):
        """Format the data from an OCS feed into a dict for pushing to InfluxDB.

        The scheme here is as follows:
            - agent_address is the "measurement" (conceptually like an SQL
              table)
            - feed names are an indexed "tag" on the data structure
              (effectively a table column)
            - keys within an OCS block's 'data' dictionary are the field names
              (effectively a table column)

        Args:
            data (dict):
                data from the OCS Feed subscription
            feed (dict):
                feed from the OCS Feed subscription, contains feed information
                used to structure our influxdb query

        """
        measurement = feed['agent_address']
        feed_tag = feed['feed_name']

        json_body = []

        # Reshape data for query
        for bk, bv in data.items():
            grouped_data_points = []
            times = bv['timestamps']
            num_points = len(bv['timestamps'])
            for i in range(num_points):
                grouped_dict = {}
                for data_key, data_value in bv['data'].items():
                    grouped_dict[data_key] = data_value[i]
                grouped_data_points.append(grouped_dict)

            for fields, time in zip(grouped_data_points, times):
                json_body.append(
                    {
                        "measurement": measurement,
                        "time": timestamp2influxtime(time),
                        "fields": fields,
                        "tags" : {
                            "feed": feed_tag
                        }
                    }
                )

        LOG.debug("payload: {p}", p=json_body)

        return json_body

    def run(self):
        """Main run iterator for the publisher. This processes all incoming
        data, removes stale providers, and writes active providers to disk.

        """
        self.process_incoming_data()

    def close(self):
        """Flushes all remaining data and closes InfluxDB connection."""
        pass


class InfluxDBAgent:
    """
    This class provide a WAMP wrapper for the data publisher. The run function
    and the data handler **are** thread-safe, as long as multiple run functions
    are not started at the same time, which should be prevented through OCSAgent.

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
            Thread-safe queue where incoming (data, feed) pairs are stored before
            being passed to the Publisher.
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

        self.agent.subscribe_on_start(self.enqueue_incoming_data,
                                      'observatory..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record',
                                    self.start_aggregate, self.stop_aggregate,
                                    startup=record_on_start)

    def enqueue_incoming_data(self, _data):
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

    def start_aggregate(self, session: ocs_agent.OpSession, params=None):
        """Process for starting data aggregation. This process will create an
        Publisher instance, which will collect and write provider data to disk
        as long as this process is running.

        """
        session.set_status('starting')
        self.aggregate = True

        LOG.debug("Instatiating Publisher class")
        publisher = Publisher(self.args.host, self.incoming_data, port=self.args.port)

        session.set_status('running')
        while self.aggregate:
            time.sleep(self.loop_time)
            publisher.run()

        publisher.close()

        return True, "Aggregation has ended"

    def stop_aggregate(self, session, params=None):
        session.set_status('stopping')
        self.aggregate = False
        return True, "Stopping aggregation"


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state',
                        default='record', choices=['idle', 'record'],
                        help="Initial state of argument parser. Can be either"
                             "idle or record")
    pgroup.add_argument('--host',
                        default='influxdb',
                        help="InfluxDB host address.")
    pgroup.add_argument('--port',
                        default=8086,
                        help="InfluxDB port.")

    return parser


if __name__ == '__main__':
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    parser = site_config.add_arguments()

    parser = make_parser(parser)

    args = parser.parse_args()

    site_config.reparse_args(args, 'InfluxDBAgent')

    agent, runner = ocs_agent.init_site_agent(args)

    influx_agent = InfluxDBAgent(agent, args)

    runner.run(agent, auto_reconnect=True)
