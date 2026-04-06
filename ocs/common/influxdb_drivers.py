from dataclasses import dataclass
from datetime import datetime, timezone


def timestamp2influxtime(time, protocol):
    """Convert timestamp for influx, always in UTC.

    Args:
        time:
            Unix 'ctime' timestamp, i.e. ``1775500953.5108523``
        protocol:
            InfluxDB protocol to format timestamp for. Either 'json' or line'.

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
class InfluxTags:
    """Stores tags to apply to a set of data within an InfluxBlock.

    Examples:
        >>> tags = InfluxTags(shared_tags={'feed': 'example_fed'},
        ...                   field_tags={'key1': 1, '_field': 'value'})


    """
    #: Tags to apply to all data points.
    shared_tags: dict

    #: Tags to apply per field, along with '_field' value to use.
    field_tags: dict = None


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
    tags: InfluxTags

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
        for k, v in self.tags.shared_tags.items():
            tag_list.append(f'{k}={v}')

        # Add unique field tags to the list and overwrite the field key
        if self.tags.field_tags:
            field_name = fields.split('=')[0]
            tags_to_add = self.tags.field_tags.get(field_name)
            for k, v in tags_to_add.items():
                if k == '_field':
                    continue
                tag_list.append(f'{k}={v}')

            # Overwrite field name with _field from tags_to_add (influxdb_tags)
            new_field_key = tags_to_add.get('_field')
            field_value = fields.split('=')[1]
            fields = f'{new_field_key}={field_value}'

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
        # Add unique field tags to the list and overwrite the field key
        if self.tags.field_tags:
            (field_name, field_value), = fields.items()  # Unpack single (k, v)
            tags_to_add = self.tags.field_tags.get(field_name)
            tags = {}
            for k, v in tags_to_add.items():
                if k == '_field':
                    continue
                tags[k] = v

            tags.update(self.tags.shared_tags)

            # Overwrite field name with _field from tags_to_add (influxdb_tags)
            new_field_key = tags_to_add.get('_field')
            fields = {new_field_key: field_value}
        else:
            tags = self.tags.shared_tags

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
            "tags": tags,
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
            # If we don't have unique field tags, group the fields together
            if self.tags.field_tags is None:
                fields_lines = self._group_fields_lines()
                for fields, time_ in zip(fields_lines, self.timestamps):
                    line = self._encode_line(fields, time_)
                    if line is not None:
                        encoded_list.append(line)

            # If we do have field_tags, encode each line separately
            else:
                grouped_data = self._group_data()
                for fields, time_ in zip(grouped_data, self.timestamps):
                    for (field, value) in fields.items():
                        f_line = _format_field_line(field, value)
                        line = self._encode_line(f_line, time_)
                        if line is not None:
                            encoded_list.append(line)

        elif protocol == 'json':
            # If we don't have unique field tags, group the fields together
            if self.tags.field_tags is None:
                grouped_data = self._group_data()
                for fields, time_ in zip(grouped_data, self.timestamps):
                    text = self._encode_json(fields, time_)
                    if text is not None:
                        encoded_list.append(text)

            # If we do have field_tags, encode each line separately
            else:
                grouped_data = self._group_data()
                for fields, time_ in zip(grouped_data, self.timestamps):
                    for (field, value) in fields.items():
                        single_field_dict = {field: value}
                        text = self._encode_json(single_field_dict, time_)
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

    The scheme used depends on whether 'influxdb_tags' are published to the Feed.

    Without 'influxdb_tags' the measurement consists of the agent address, i.e.
    ``address_root.instance_id``, there is a single tag for the feed name, and
    each data field from the OCS feed is used directly as the field name in
    InfluxDB. This structure, however, is not ideal for InfluxDB query
    performance.

    When 'influxdb_tags' are provided by the agent then the measurement becomes
    the agent class, and the address root and instance-id are added as tags.
    The 'influxdb_tags' are also used to add additional tags and provide a
    simple field name. See the examples below.

    Args:
        data (dict):
            Data from the OCS Feed subscription.
        feed (dict):
            Feed from the OCS Feed subscription, contains feed information
            used to structure our influxdb query.
        protocol (str):
            Protocol for writing data. Either 'line' or 'json'.

    Returns:
        list: Data ready to publish to influxdb, in the specified protocol.

    Examples:
        >>> # without 'influxdb_tags'
        >>> format_data(data, feed, protocol='line')
        ['observatory.fake-data1,feed=false_temperatures channel_00=0.20307 1775502374078489088',
         'observatory.fake-data1,feed=false_temperatures channel_01=0.35795 1775502374078489088',
         'observatory.fake-data1,feed=false_temperatures channel_00=0.20548 1775502375078489088',
         'observatory.fake-data1,feed=false_temperatures channel_01=0.36313 1775502375078489088']

        >>> # with 'influxdb_tags'
        >>> format_data(data, feed, protocol='line')
        ['FakeDataAgent,feed=false_temperatures,address_root=observatory,instance_id=fake-data1,channel=0 temperature=0.20307 1775502374078489088',
         'FakeDataAgent,feed=false_temperatures,address_root=observatory,instance_id=fake-data1,channel=1 temperature=0.35795 1775502374078489088',
         'FakeDataAgent,feed=false_temperatures,address_root=observatory,instance_id=fake-data1,channel=0 temperature=0.20548 1775502375078489088',
         'FakeDataAgent,feed=false_temperatures,address_root=observatory,instance_id=fake-data1,channel=1 temperature=0.36313 1775502375078489088']

    """
    # Load data into InfluxBlock objects.
    blocks = []
    for _, bv in data.items():
        shared_tags = {'feed': feed['feed_name']}
        measurement = feed.get('agent_address')
        if bv.get('influxdb_tags'):
            measurement = feed.get('agent_class')
            shared_tags['address_root'] = feed['agent_address'].split('.')[0]
            shared_tags['instance_id'] = feed['agent_address'].split('.')[1]
        tags = InfluxTags(
            shared_tags=shared_tags,
            field_tags=bv.get('influxdb_tags'))
        if 'timestamp' in bv:
            bv = _convert_single_to_group(bv)
        block = InfluxBlock(
            block_name=bv['block_name'],
            data=bv['data'],
            timestamps=bv['timestamps'],
            measurement=measurement,
            tags=tags)
        blocks.append(block)

    # There is typically only one block, but just in case.
    formatted_data = []
    for block in blocks:
        formatted_data.extend(block.encode(protocol=protocol))

    return formatted_data
