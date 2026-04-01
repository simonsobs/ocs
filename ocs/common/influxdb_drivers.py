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
class ReceivedBlock:
    block_name: str
    data: dict
    timestamps: list
    influxdb_tags: dict = None

    def group_data(self):
        # Reshape data for query
        grouped_data_points = []
        num_points = len(self.timestamps)
        for i in range(num_points):
            grouped_dict = {}
            for data_key, data_value in self.data.items():
                grouped_dict[data_key] = data_value[i]
            grouped_data_points.append(grouped_dict)

        return grouped_data_points, self.timestamps

    def encoded(self, protocol='line'):
        # I wouldn't mind having some structure that checked for
        # 'influxdb_tags' and if it had those, then ran one set of if/elif/else
        # for the various protocols

        # then if it didn't have influxdb_tags ran the below set of
        # if/elif/else for the protocols
        # the other option is to try to flip it so that it checks for protocol
        # first, then does the manipulations required to reshape

        # would some dataclass that can form the appropriate structures work
        # better? maybe...

        # This could just do .encoded('line') or .encoded('json') based on
        # which protocol and do the grouping/rearranging internally

        if self.influxdb_tags is None:
            # do old grouping methods
            pass
        else:
            # do new assembly of outputs w/tags
            pass


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

H
    Returns:
        list: Data ready to publish to influxdb, in the specified protocol.

    Examples:
        data = {'temps': {'block_name': 'temps',
                          'data': {'channel_00': [0.0861292206532646, 0.08767502826731405, 0.09074201939982668],
                                   'channel_01': [0.040572476754158676, 0.04176234998637523, 0.044872031531513375]},
                          'influxdb_tags': {'channel_00':
                                                {'channel': 0, '_field': 'temperature'},
                                            'channel_01':
                                                {'channel': 1, '_field': 'temperature'}},
                          'timestamps': [1775065084.3634055, 1775065085.3634055, 1775065086.3634055]}}
        json_body = ['observatory.fake-data1,feed=false_temperatures channel_00=0.0861292206532646,channel_01=0.040572476754158676 1775065084363405568',
                     'observatory.fake-data1,feed=false_temperatures channel_00=0.08767502826731405,channel_01=0.04176234998637523 1775065085363405568',
                     'observatory.fake-data1,feed=false_temperatures channel_00=0.09074201939982668,channel_01=0.044872031531513375 1775065086363405568']

    """
    if protocol == 'line':
        measurement = feed['agent_address']
        feed_tag = feed['feed_name']
        tags = f"feed={feed_tag}"

        json_body = []

        blocks = []
        for _, bv in data.items():
            blocks.append(ReceivedBlock(**bv))

        # print(blocks)

        # print('DATA:', data)
        # Old, non-tag, way to reshape data for query
        grouped_data_points, times = _group_data(data)
        block_grouped, block_times = blocks[0].group_data()
        assert grouped_data_points == block_grouped
        assert times == block_times
        print('GROUPS:', grouped_data_points)

        # print('\n')
        fields_lines = []
        for fields, time_ in zip(grouped_data_points, times):
            field_line = []
            for mk, mv in fields.items():
                f_line = _format_field_line(mk, mv)
                field_line.append(f_line)

            fields_line = ','.join(field_line)
            fields_lines.append(fields_line)
        # Old, non-tag, way to reshape data for query

        for fields, time_ in zip(fields_lines, times):
            print('SINGLE:', fields_line, time_)
            text = _format_line(measurement, time_, fields, tags)
            if text is not None:
                json_body.append(text)

        print('ALL:', fields_lines)

    elif protocol == 'json':
        measurement = feed['agent_address']
        feed_tag = feed['feed_name']

        json_body = []

        print('DATA:', data)
        # Reshape data for query
        grouped_data_points, times = _group_data(data)
        print('GROUPS:', grouped_data_points)

        for fields, time_ in zip(grouped_data_points, times):
            tags = {"feed": feed_tag}
            text = _format_json(measurement, time_, fields, tags)
            if text is not None:
                json_body.append(text)

    else:
        print(f"Protocol '{protocol}' not supported.")

    return json_body


def _group_data(data):
    # Reshape data for query
    grouped_data_points = []
    # there should only ever be 1 key, value pair in these blocks
    for _, bv in data.items():
        times = bv['timestamps']
        num_points = len(bv['timestamps'])
        for i in range(num_points):
            grouped_dict = {}
            for data_key, data_value in bv['data'].items():
                grouped_dict[data_key] = data_value[i]
            grouped_data_points.append(grouped_dict)

    return grouped_data_points, times


def _format_json(measurement, time, fields, tags):
    try:
        t_json = timestamp2influxtime(time, protocol='json')
    except OverflowError:
        print(f"Warning: Cannot convert {time} to an InfluxDB compatible time. "
              + "Dropping this data point.")
        return
    json = {
        "measurement": measurement,
        "time": t_json,
        "fields": fields,
        "tags": tags,
    }
    return json


def _format_line(measurement, time, fields, tags):
    try:
        t_line = timestamp2influxtime(time, protocol='line')
    except OverflowError:
        print(f"Warning: Cannot convert {time} to an InfluxDB compatible time. "
              + "Dropping this data point.")
        return
    line = f"{measurement},{tags} {fields} {t_line}"
    return line
