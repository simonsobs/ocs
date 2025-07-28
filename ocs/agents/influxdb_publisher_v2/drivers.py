import time
import txaio

from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, WriteOptions
from influxdb_client.client.exceptions import InfluxDBError
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import NewConnectionError, ProtocolError
from influxdb_client.client.write_api import WriteType

from ocs.common.influxdb_drivers import format_data

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


class Publisher:
    """
    Data publisher. This manages data to be published to the InfluxDB.

    This class should only be accessed by a single thread. Data can be passed
    to it by appending it to the referenced `incoming_data` queue.

    Args:
        incoming_data (queue.Queue):
            A thread-safe queue of (data, feed) pairs.
        database (str):
            database name within InfluxDB to publish to
        protocol (str, optional):
            Protocol for writing data. Either 'line' or 'json'.
        gzip (bool, optional):
            compress influxdb requsts with gzip
        operate_callback (callable, optional):
            Function to call to see if failed connections should be
            retried (to prevent a thread from locking).

    Attributes:
        db (str):
            database name within InfluxDB to publish to (from database arg)
        incoming_data:
            data to be published
        client:
            InfluxDB client connection

    """

    def __init__(self, database, incoming_data, org, protocol='line',
                 gzip=False, operate_callback=None):
        self.db = database
        self.incoming_data = incoming_data
        self.org = org
        self.protocol = protocol
        self.gzip = gzip

        print(f"gzip encoding enabled: {gzip}")
        print(f"data protocol: {protocol}")

        self.client = InfluxDBClient.from_env_properties()
        self.write_client = self.client.write_api(write_options=WriteOptions(write_type=WriteType.synchronous, 
                                                                             batch_size=10000))

        bucket = None
        # ConnectionError here is indicative of InfluxDB being down
        while bucket is None:
            try:
                buckets_api = self.client.buckets_api()
                bucket = buckets_api.find_bucket_by_name(self.db)
            except (RequestsConnectionError, NewConnectionError, ProtocolError):
                LOG.error("Connection error, attempting to reconnect to DB.")
                self.client = InfluxDBClient.from_env_properties()
                self.write_client = self.client.write_api(write_options=WriteOptions(write_type=WriteType.synchronous, 
                                                                                     batch_size=10000))
                time.sleep(1)
            if operate_callback and not operate_callback():
                break

        if self.db != bucket.name:
            print(f"{self.db} DB doesn't exist, creating DB")
            self.client.buckets_api().create_bucket(bucket_name=self.db,
                                                    org=self.org)

    def process_incoming_data(self):
        """
        Takes all data from the incoming_data queue, and writes them to the
        InfluxDB.
        """
        payload = []
        LOG.debug("Pulling data from queue.")
        while not self.incoming_data.empty():
            data, feed = self.incoming_data.get()
            if feed['agg_params'].get('exclude_influx', False):
                continue

            # Formatted for writing to InfluxDB
            payload.extend(format_data(data, feed, protocol=self.protocol))

        # Skip trying to write if payload is empty
        if not payload:
            return

        try:
            LOG.debug("payload: {p}", p=payload)
            self.write_client.write(bucket=self.db, record=payload)
            LOG.debug("wrote payload to influx")
        except (RequestsConnectionError, NewConnectionError, ProtocolError):
            LOG.error("InfluxDB unavailable, attempting to reconnect.")
            self.client = InfluxDBClient.from_env_properties()
            self.write_client = self.client.write_api(write_options=WriteOptions(write_type=WriteType.synchronous, 
                                                                                 batch_size=10000))
        except InfluxDBError as err:
            LOG.error("InfluxDB Client Error: {e}", e=err)

    def run(self):
        """Main run iterator for the publisher. This processes all incoming
        data, removes stale providers, and writes active providers to disk.

        """
        self.process_incoming_data()

    def close(self):
        """Flushes all remaining data and closes InfluxDB connection."""
        pass
