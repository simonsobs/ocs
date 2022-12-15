.. highlight:: rst

.. _registry:

==============
Registry Agent
==============

The Registry Agent tracks all currently running Agents on the OCS network,
providing the ability to monitor the status of each Agent's Tasks and Processes
through the :ref:`operation_monitor`.

.. argparse::
   :module: ocs.agents.registry.agent
   :func: make_parser
   :prog: agent.py

Configuration File Examples
----------------------------

Below are configuration examples for the ocs config file and for running the
Agent in a docker container.

OCS Site Config
```````````````

An example site-config-file block::

    { 'agent-class': 'RegistryAgent',
      'instance-id': 'registry',
      'arguments': [
        ['--wait-time', 30]
      ]},

Docker Compose
``````````````

An example docker-compose configuration::

    ocs-registry:
        image: simonsobs/ocs:latest
        container_name: ocs-registry
        hostname: ocs-docker
        user: "9000"
        environment:
          - INSTANCE_ID=registry
        volumes:
          - ${OCS_CONFIG_DIR}:/config

Description
-----------

The registry agent is used to keep track of currently running active agents.
It listens to the heartbeat feeds of all agents on the crossbar server,
and keeps track of the last heartbeat time of each agent and whether
or not each agent has agent has "expired" (gone 5 seconds without a heartbeat).

This check happens in the registry's single "main" process. The session.data
object of this process is set to a dict of agents on the system, including
their last heartbeat time, whether they have expired, the time at which they
expired, and a dictionary of their operation codes.  This data can the be
viewed by checking the session variable of the main process.

For instance, the following code will print agent's that have been on the system
since the registry started running::

    from ocs.ocs_client import OCSClient

    registry_client = OCSClient('registry')
    status, msg, session = registry_client.main.status()

    print(session['data'])

which will print a dictionary that might look like::

    {
      "observatory.aggregator": {
        "expired": False,
        "time_expired": None,
        "last_updated": 1669925713.4082503,
        "op_codes": {
          "record": 3
        },
        "agent_class": "AggregatorAgent",
        "agent_address": "observatory.aggregator"
      },
      "observatory.fake-hk-agent-01": {
        "expired": False,
        "time_expired": None,
        "last_updated": 1669925945.7575383,
        "op_codes": {
          "acq": 3,
          "set_heartbeat": 1,
          "delay_task": 1
        },
        "agent_class": "FakeDataAgent",
        "agent_address": "observatory.fake-hk-agent-01"
      }
    }


.. _operation_monitor:

Operation Monitor
`````````````````

The registry is also used to track the status of each agent's tasks and
processes. `Operation codes` for each operation are regularly passed through an
agent's heartbeat feed, which the registry assembles and publishes through its
own OCS feed. This makes it possible to monitor individual operation states in
grafana and to easily set alerts when a process stops running or when a task
fails.

By mapping the enumeration values described in the ``OpCode`` documentation in
the :ref:`ocs_base api <ocs_base_api>`, one can make a grafana panel to monitor
all operations on a network as pictured below:

.. image:: ../_static/operation_monitor_screenshot.png




Agent API
---------

.. autoclass:: ocs.agents.registry.agent.Registry
    :members:

Supporting APIs
---------------
.. autoclass:: ocs.agents.registry.agent.RegisteredAgent
    :members:
