.. highlight:: rst

.. _influxdb_publisher:

========================
InfluxDB Publisher Agent
========================

The InfluxDB Publisher Agent acts like the OCS Aggregator, but instead of
writing to file it will publish all recorded OCS data feeds to an InfluxDB
instance running somewhere on the network.

OCS Configuration
-----------------
Add an InfluxDBAgent to your OCS configuration file::

      {'agent-class': 'InfluxDBAgent',
       'instance-id': 'influxagent',
       'arguments': [['--initial-state', 'record'],
                     ['--host', 'influxdb'],
                     ['--port', 8086]]},

docker-compose Configuration
----------------------------
Add the InfluxDB Publisher Agent container to your docker-compose file::

  ocs-influxdb-publisher:
    image: simonsobs/ocs-influxdb-publisher-agent
    hostname: ocs-docker
    volumes:
      - ${OCS_CONFIG_DIR}:/config:ro

You will also need an instance of InfluxDB running somewhere on your network.
This likely should go in a separte docker-compose file so that it remains
online at all times.

::

  influxdb:
    image: "influxdb:1.7"
    container_name: "influxdb"
    restart: always
    ports:
      - "8086:8086"
    volumes:
      - /srv/influxdb:/var/lib/influxdb
