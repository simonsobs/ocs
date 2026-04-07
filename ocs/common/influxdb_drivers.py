from dataclasses import dataclass
from datetime import datetime, timezone


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


@dataclass
class InfluxBlock:
    """Holds and can convert the data and feed information into a format
    suitable for publishing to InfluxDB.

    """
    #: OCS Block name.
    block_name: str

    #: OCS data, as it comes across the feed.
    data: dict

    #: Corresponding timestamps for the data.
    timestamps: list

    #: Measurement name to publish to in InfluxDB.
    measurement: str

    #: Tags to apply to the measurements.
    tags: dict

    def _group_data(self):
        """Takes the block structured data and groups each data point in a set
        of fields so they can be combined with the corresponding timestamp.

        Example:
            This takes something of the form::

                {'channel_00': [-0.0943, -0.0965],
                 'channel_01': [-0.0082, -0.0086]}

            and shapes it into the form::

                [{'channel_00': -0.0943, 'channel_01': -0.0082},
                 {'channel_00': -0.0965, 'channel_01': -0.0086}]

            This is the form needed to pass directly to the 'json' format.

        """
        grouped_data = []
        for i in range(len(self.timestamps)):
            grouped_dict = {}
            for k, v in self.data.items():
                grouped_dict[k] = v[i]
            grouped_data.append(grouped_dict)

        return grouped_data

    def _group_fields_lines(self):
        """Takes the block structured data and groups each data point into a
        set of fields formatted for the 'line' protocol that can be combined
        with the corresponding timestamp.

        Example:
            This takes something of the form::

                {'channel_00': [-0.1170, -0.1180, -0.1153],
                 'channel_01': [-0.0241, -0.0267, -0.0226]}

            and shapes it into the form::

                ['channel_00=-0.1170,channel_01=-0.0241',
                 'channel_00=-0.1180,channel_01=-0.0267',
                 'channel_00=-0.1153,channel_01=-0.0226']

            This is the form needed to pass directly to the 'line' format.

        """
        grouped_data = self._group_data()
        fields_lines = []
        for fields in grouped_data:
            fields_line = []
            for mk, mv in fields.items():
                f_line = _format_field_line(mk, mv)
                fields_line.append(f_line)

            field_line = ','.join(fields_line)
            fields_lines.append(field_line)
        return fields_lines

    def _encode_line(self, fields, timestamp):
        """Given the fields and timestamps, encode them for use in the 'line'
        protocol.

        Args:
            fields (str): Comma separated list of fields.
            timestamp (float): Unix timestamp.

        Returns:
            str: Complete 'line' protocol string.

        Example:
            An example of the formatting::

                >>> block._encode_line('channel_00=-0.0341,channel_01=0.0612', 1775162753.7786078)
                observatory.fake-data1,feed=false_temperatures channel_00=-0.0341,channel_01=0.0612 1775162753778607872

        """
        # Convert json format tags to line format
        tag_list = []
        for k, v in self.tags.items():
            tag_list.append(f"{k}={v}")
        tags = ','.join(tag_list)

        try:
            t_influx = timestamp2influxtime(timestamp, protocol='line')
        except OverflowError:
            print(f"Warning: Cannot convert {timestamp} to an InfluxDB compatible time. "
                  + "Dropping this data point.")
            return

        line = f"{self.measurement},{tags} {fields} {t_influx}"
        return line

    def _encode_json(self, fields, timestamp):
        """Given the fields and timestamps, encode them for use in the 'json'
        protocol.

        Args:
            fields (dict): Dictionary with the fields and their associated values.
            timestamp (float): Unix timestamp.

        Returns:
            dict: Complete 'json' protocol dict.

        Example:
            An example of the formatting::

                >>> block._encode_json({'channel_00': -0.1149, 'channel_01': -0.0038}, 1775163570.7786078)
                {'measurement': 'observatory.fake-data1',
                 'time': '2026-04-02T20:59:30.778608',
                 'fields': {'channel_00': -0.1149, 'channel_01': -0.0038},
                 'tags': {'feed': 'false_temperatures'}}

        """
        try:
            t_influx = timestamp2influxtime(timestamp, protocol='json')
        except OverflowError:
            print(f"Warning: Cannot convert {timestamp} to an InfluxDB compatible time. "
                  + "Dropping this data point.")
            return

        json = {
            "measurement": self.measurement,
            "time": t_influx,
            "fields": fields,
            "tags": self.tags,
        }
        return json

    def encode(self, protocol='line'):
        """Encode Block data into InfluxDB compatible format for the given
        protocol.

        Args:
            protocol (str): Protocol to use to publish to InfluxDB. Either
                'line' or 'json'. Defaults to 'line'.

        Returns:
            list:
                List of encoded data points, formatted to be used by the
                InfluxDB client.

        """
        encoded_list = []
        if protocol == 'line':
            fields_lines = self._group_fields_lines()
            for fields, time_ in zip(fields_lines, self.timestamps):
                line = self._encode_line(fields, time_)
                if line is not None:
                    encoded_list.append(line)

        elif protocol == 'json':
            grouped_data = self._group_data()
            for fields, time_ in zip(grouped_data, self.timestamps):
                text = self._encode_json(fields, time_)
                if text is not None:
                    encoded_list.append(text)
        else:
            print(f"Protocol '{protocol}' not supported.")

        return encoded_list


def _convert_single_to_group(message):
    """Convert a single sample 'timestamp' message to the co-sampled group
    'timestamps' format, which we can handle already.

    Args:
        message (dict): Single sample 'timestamp' message from the OCS feed.

    Notes:
        This doesn't take the data directly from the feed, but the block dict
        only.

    """
    message['timestamps'] = [message['timestamp']]
    new_data = {}
    for field, value in message['data'].items():
        new_data[field] = [value]
    message['data'] = new_data
    message.pop('timestamp')
    return message


def format_data(data, feed, protocol):
    """Format the data from an OCS feed for publishing to InfluxDB.

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
    # Load data into InfluxBlock objects.
    blocks = []
    for _, bv in data.items():
        tags = {'feed': feed['feed_name']}
        if 'timestamp' in bv:
            bv = _convert_single_to_group(bv)
        block = InfluxBlock(
            block_name=bv['block_name'],
            data=bv['data'],
            timestamps=bv['timestamps'],
            measurement=feed['agent_address'],
            tags=tags)
        blocks.append(block)

    # There is typically only one block, but just in case.
    formatted_data = []
    for block in blocks:
        formatted_data.extend(block.encode(protocol=protocol))

    return formatted_data
