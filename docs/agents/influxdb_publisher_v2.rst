.. highlight:: rst

.. _influxdb_publisher_v2:

========================
InfluxDB Publisher v2 Agent
========================

The InfluxDB Publisher v2 Agent is an upgraded InfluxDB Publisher Agent that
uses the influxdb-client package instead of influxdb package to work with
InfluxDB v2.

.. argparse::
   :module: ocs.agents.influxdb_publisher_v2.agent
   :func: make_parser
   :prog: agent.py

Configuration File Examples
---------------------------

Below are configuration examples for the ocs config file and for running the
Agent in a docker container. Also included is an example for setting up
Grafana to display data from InfluxDB.

OCS Site Config
```````````````

Add an InfluxDBAgent to your OCS configuration file::

      {'agent-class': 'InfluxDBAgentv2',
       'instance-id': 'influxagent',
       'arguments': ['--initial-state', 'record',
                     '--org', 'ocs',
                     '--database', 'ocs_feeds']},

Docker Compose
``````````````

Add the InfluxDB Publisher v2 Agent container to your docker-compose file::

  ocs-influxdb-publisher-v2:
    image: simonsobs/ocs:latest
    hostname: ocs-docker
    environment:
      - INSTANCE_ID=influxagent
    volumes:
      - ${OCS_CONFIG_DIR}:/config:ro
    env_file:
      - .env

Your .env file should contain credentials for the InfluxDB v2 database::

  INFLUXDB_V2_URL=http://influxdb:8086
  INFLUXDB_V2_ORG=ocs
  INFLUXDB_V2_BUCKET=ocs_feeds
  INFLUXDB_V2_TOKEN=<your-token>

You will also need an instance of InfluxDB v2 running somewhere on your network.
This likely should go in a separate docker-compose file so that it remains
online at all times. An example compose file would look like::

  services:
    influxdb:
      image: "influxdb:2.7"
      container_name: "influxdb"
      restart: always
      ports:
        - "8086:8086"
      environment:
        - INFLUXDB_HTTP_LOG_ENABLED=false
      volumes:
        - /srv/influxdb2:/var/lib/influxdb2

  networks:
    default:
      external:
        name: ocs-net

.. note::
    This separate docker-compose file setup depends on having a docker network
    that connects your various docker-compose files. On a single-node setup
    this can be accomplished with the network settings above in each docker-compose
    file.

    You then need to create the docker network with::

       $ docker network create --driver bridge ocs-net

    Containers on the network should then be able to communicate.

For more information about configuring Docker Compose files, see the `Compose
file reference`_.

.. _`Compose file reference`: https://docs.docker.com/compose/compose-file/

Database Migration
``````````````````

Follow instructions to `Upgrade from InfluxDB 1.x to 2.7 with Docker <upgrade_>`_.

.. _`upgrade`: https://docs.influxdata.com/influxdb/v2/install/upgrade/v1-to-v2/docker/

Grafana
```````

Once your InfluxDB v2 container and publisher are configured and running you will
need to create an InfluxDB data source in Grafana. To do so, we add an InfluxDB
data source with the URL ``http://influxdb:8086``, and the Database
(default "ocs_feeds", but this can be customized in your OCS config file.) The
Name of the Data Source is up to you, in this example we set it to "OCS Feeds".
Note that if you migrated from InfluxDB 1.x to 2.7, this process is slightly
different from adding an InfluxDB 1.x data source, as the auth token is required.

Follow instructions to `Configure your InfluxDB connection <configure_>`_ for InfluxDB v2.

.. _`configure`: https://docs.influxdata.com/influxdb/v2/tools/grafana/?t=InfluxQL#configure-your-influxdb-connection

.. note::
    The "ocs_feeds" database (or whatever you choose to name the database) will
    not exist until the first time the InfluxDB Publisher Agent has successfully
    connected to the InfluxDB.

.. image:: ../_static/grafana_influxdb_data_source.jpg

In a dashboard, create a new panel. Each panel can have a different Data
Source, which is selected at the top of the Metrics tab. Select our "OCS Feeds"
data source. You'll then see the rich query editor for your InfluxDB data
source. Each OCS Agent shows up as a "measurement" (here "observatory.LSSIM"
and "observatory.LSSIM2"). Each feed published by an agent is an InfluxDB tag
(here "temperatures" is our only feed.) Finally, each field is available within
the SELECT query.

.. image:: ../_static/grafana_influxdb_panel_example.jpg

For more information about using InfluxDB in Grafana, see the `Grafana Documentation`_.

.. _`Grafana Documentation`: https://grafana.com/docs/features/datasources/influxdb/

Agent API
---------

.. autoclass:: ocs.agents.influxdb_publisher_v2.agent.InfluxDBAgentv2
    :members:


Supporting APIs
---------------

.. autoclass:: ocs.agents.influxdb_publisher_v2.agent.Publisher
    :members:
