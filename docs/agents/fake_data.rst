===============
Fake Data Agent
===============

The Fake Data Agent is provided with OCS to help demonstrate and debug issues
with data aggregation and display. It will generate random data and pass it to
an OCS feed.

Command-line / site config args
-------------------------------

.. argparse::
   :module: agents.fake_data.fake_data_agent
   :func: add_agent_args
   :prog: fake_data_agent.py

Configuration File Examples
---------------------------
Below are configuration examples for the ocs config file and for running the Agent in a docker container.

ocs-config
``````````
To configure the Fake Data Agent we need to add a FakeDAtaAgent block to our
ocs configuration file. Here is an example configuration block using all of the
available arguments::

    {'agent-class': 'FakeDataAgent',
     'instance-id': 'fake-data1',
     'arguments': [['--mode', 'acq'],
                   ['--num-channels', '16'],
                   ['--sample-rate', '4']]},

Docker
``````
The Fake Data Agent can also be run in a Docker container. An example
docker-compose service configuration is shown here::

    fake-data1:
        image: simonsobs/ocs-fake-data-agent
        hostname: ocs-docker
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro
        command:
          - "--instance-id=fake-data1"

Agent Operations
----------------

.. autoclass:: agents.fake_data.fake_data_agent.FakeDataAgent
    :members:
