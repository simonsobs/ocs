import time
import txaio

from datetime import datetime, timezone
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import ConnectionError as RequestsConnectionError

# For logging
txaio.use_twisted()
LOG = txaio.make_logger()


def timestamp2influxtime(time, protocol):
    """Convert timestamp for influx, always in UTC.

    Args:
        time:
            ctime timestamp
        protocol:
            'json' or line'

    """
    if protocol == 'json':
        t_dt = datetime.fromtimestamp(time)
        # InfluxDB expects UTC by default
        t_dt = t_dt.astimezone(tz=timezone.utc)
        influx_t = t_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    elif protocol == 'line':
        influx_t = int(time * 1e9)  # ns
    return influx_t


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
        gzip (bool, optional):
            compress influxdb requsts with gzip
        operate_callback (callable, optional):
            Function to call to see if failed connections should be
            retried (to prevent a thread from locking).

    Attributes:
        host (str):
            host for InfluxDB instance.
        port (int, optional):
            port for InfluxDB instance, defaults to 8086.
        db (str):
            database name within InfluxDB to publish to (from database arg)
        incoming_data:
            data to be published
        client:
            InfluxDB client connection

    """

    def __init__(self, host, database, incoming_data, port=8086, protocol='line',
                 gzip=False, operate_callback=None):
        self.host = host
        self.port = port
        self.db = database
        self.incoming_data = incoming_data
        self.protocol = protocol
        self.gzip = gzip

        print(f"gzip encoding enabled: {gzip}")
        print(f"data protocol: {protocol}")

        self.client = InfluxDBClient(host=self.host, port=self.port, gzip=gzip)

        db_list = None
        # ConnectionError here is indicative of InfluxDB being down
        while db_list is None:
            try:
                db_list = self.client.get_list_database()
            except RequestsConnectionError:
                LOG.error("Connection error, attempting to reconnect to DB.")
                self.client = InfluxDBClient(host=self.host, port=self.port, gzip=gzip)
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
            payload.extend(self.format_data(data, feed, protocol=self.protocol))

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
            self.client = InfluxDBClient(host=self.host, port=self.port, gzip=self.gzip)
            self.client.switch_database(self.db)
        except InfluxDBClientError as err:
            LOG.error("InfluxDB Client Error: {e}", e=err)
        except InfluxDBServerError as err:
            LOG.error("InfluxDB Server Error: {e}", e=err)

    @staticmethod
    def _format_field_line(field_key, field_value):
        """Format key-value pair for InfluxDB line protocol."""
        # Strings must be in quotes for line protocol
        if isinstance(field_value, str):
            line = f'{field_key}="{field_value}"'
        else:
            line = f"{field_key}={field_value}"
        # Don't append 'i' to bool, which is a subclass of int
        if isinstance(field_value, int) and not isinstance(field_value, bool):
            line += "i"
        return line

    @staticmethod
    def format_data(data, feed, protocol):
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
            protocol (str):
                Protocol for writing data. Either 'line' or 'json'.

        Returns:
            list: Data ready to publish to influxdb, in the specified protocol.

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

            for fields, time_ in zip(grouped_data_points, times):
                if protocol == 'line':
                    fields_line = []
                    for mk, mv in fields.items():
                        f_line = Publisher._format_field_line(mk, mv)
                        fields_line.append(f_line)

                    measurement_line = ','.join(fields_line)
                    t_line = timestamp2influxtime(time_, protocol='line')
                    line = f"{measurement},feed={feed_tag} {measurement_line} {t_line}"
                    json_body.append(line)
                elif protocol == 'json':
                    json_body.append(
                        {
                            "measurement": measurement,
                            "time": timestamp2influxtime(time_, protocol='json'),
                            "fields": fields,
                            "tags": {
                                "feed": feed_tag
                            }
                        }
                    )
                else:
                    LOG.warn(f"Protocol '{protocol}' not supported.")

        return json_body

    def run(self):
        """Main run iterator for the publisher. This processes all incoming
        data, removes stale providers, and writes active providers to disk.

        """
        self.process_incoming_data()

    def close(self):
        """Flushes all remaining data and closes InfluxDB connection."""
        pass
