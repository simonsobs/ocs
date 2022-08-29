.. _barebones:

===============
Barebones Agent
===============

The Barebones Agent is provided with OCS to provide a starting point for Agent
development. It is heavily used throughout the Agent development guide.

Configuration File Examples
---------------------------

Below are configuration examples for the ocs config file and for running the
Agent in a docker container.

OCS Site Config
```````````````

To configure the Fake Data Agent we need to add a FakeDataAgent block to our
ocs configuration file. Here is an example configuration block using all of the
available arguments::

    {'agent-class': 'BarebonesAgent',
     'instance-id': 'barebones-1',
     'arguments': []},

Agent API
---------

.. autoclass:: ocs.agents.barebones.agent.BarebonesAgent
    :members:
