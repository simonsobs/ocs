import os
import time

from dataclasses import dataclass, asdict

import txaio

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import ConnectionError as RequestsConnectionError

from ocs.common.influxdb_drivers import format_data

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


def _get_credentials():
    """Read credentials from environment variable or file.

    Reads from either `INFLUXDB_USERNAME`, `INFLUXDB_PASSWORD`,
    `INFLUXDB_USERNAME_FILE`, or `INFLUXDB_PASSWORD_FILE`. Precedence is given
    to the non-`_FILE` variables.

    Returns:
        A tuple of (username, password). Defaults to ('root', 'root') if none
        of the environment variables are present.

    """
    username_file = os.environ.get('INFLUXDB_USERNAME_FILE')
    password_file = os.environ.get('INFLUXDB_PASSWORD_FILE')

    username = None
    password = None
    if username_file is not None:
        with open(username_file, 'r', encoding="utf-8") as f:
            username = f.read().rstrip('\r\n')
    if password_file is not None:
        with open(password_file, 'r', encoding="utf-8") as f:
            password = f.read().rstrip('\r\n')

    username_default = 'root' if username is None else username
    password_default = 'root' if password is None else password

    username = os.environ.get('INFLUXDB_USERNAME', username_default)
    password = os.environ.get('INFLUXDB_PASSWORD', password_default)

    return username, password


@dataclass
class _InfluxDBClientArgs:
    """Object to hold arguments passed to InfluxDBClient.

    https://influxdb-python.readthedocs.io/en/latest/api-documentation.html#influxdb.InfluxDBClient

    """
    host: str
    port: int
    username: str
    password: str
    ssl: bool
    verify_ssl: bool
    gzip: bool


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
        database (str):
            database name within InfluxDB to publish to
        port (int, optional):
            port for InfluxDB instance, defaults to 8086.
        protocol (str, optional):
            Protocol for writing data. Either 'line' or 'json'.
        ssl (bool, optional):
            Use https instead of http to connect to InfluxDB, defaults to False.
        verify_ssl (bool, optional):
            Verify SSL certificates for HTTPS requests, defaults to False.
        gzip (bool, optional):
            compress influxdb requsts with gzip
        operate_callback (callable, optional):
            Function to call to see if failed connections should be
            retried (to prevent a thread from locking).

    Attributes:
        db (str):
            database name within InfluxDB to publish to (from database arg)
        protocol (str, optional):
            Protocol for writing data. Either 'line' or 'json'.
        incoming_data:
            data to be published
        client_args:
            arguments passed to InfluxDB client
        client:
            InfluxDB client connection

    """

    def __init__(self,
                 host,
                 database,
                 incoming_data,
                 port=8086,
                 protocol='line',
                 ssl=False,
                 verify_ssl=False,
                 gzip=False,
                 operate_callback=None):
        self.db = database
        self.incoming_data = incoming_data
        self.protocol = protocol

        print(f"gzip encoding enabled: {gzip}")
        print(f"data protocol: {protocol}")

        username, password = _get_credentials()

        self.client_args = _InfluxDBClientArgs(
            host=host,
            port=port,
            username=username,
            password=password,
            ssl=ssl,
            verify_ssl=verify_ssl,
            gzip=gzip)
        self.client = InfluxDBClient(**asdict(self.client_args))

        db_list = None
        # ConnectionError here is indicative of InfluxDB being down
        while db_list is None:
            try:
                db_list = self.client.get_list_database()
            except RequestsConnectionError:
                LOG.error("Connection error, attempting to reconnect to DB.")
                self.client = InfluxDBClient(**asdict(self.client_args))
                time.sleep(1)
            except InfluxDBClientError as err:
                if err.code == 401:
                    LOG.error("Failed to authenticate. Check your credentials.")
                else:
                    LOG.error(f"Unknown client error: {err}")
                time.sleep(1)
            if operate_callback and not operate_callback():
                break

        db_names = [x['name'] for x in db_list]

        if self.db not in db_names:
            print(f"{self.db} DB doesn't exist, creating DB")
            self.client.create_database(self.db)

        self.client.switch_database(self.db)

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
            self.client.write_points(payload,
                                     batch_size=10000,
                                     protocol=self.protocol,
                                     )
            LOG.debug("wrote payload to influx")
        except RequestsConnectionError:
            LOG.error("InfluxDB unavailable, attempting to reconnect.")
            self.client = InfluxDBClient(**asdict(self.client_args))
            self.client.switch_database(self.db)
        except InfluxDBClientError as err:
            LOG.error("InfluxDB Client Error: {e}", e=err)
        except InfluxDBServerError as err:
            LOG.error("InfluxDB Server Error: {e}", e=err)

    def run(self):
        """Main run iterator for the publisher. This processes all incoming
        data, removes stale providers, and writes active providers to disk.

        """
        self.process_incoming_data()

    def close(self):
        """Flushes all remaining data and closes InfluxDB connection."""
        pass
