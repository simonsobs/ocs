.. highlight:: rst

.. _registry:

Registry Agent
=======================

The registry agent is used to keep track of currently running active agents.
Agents are automatically registered OnJoin, and the registry monitors
each agent's heartbeat to remove the agent if it disconnects.

One can keep track of active agents by monitoring the *agent_activity*
feed, which will publish whenever an agent is registered, unregistered,
or updated. Calling the *dump_agents* task will print the current status
of all active agents to the feed.

API
---

.. autoclass:: agents.registry.registry.Registry
    :members:
