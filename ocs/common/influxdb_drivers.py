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
                    f_line = _format_field_line(mk, mv)
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
                print(f"Protocol '{protocol}' not supported.")

    return json_body
