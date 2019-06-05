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

Docker Configuration
--------------------
The docker image for the registry agent is
``grumpy.physics.yale.edu/ocs-registry-agent:latest``.  Here is an example
Docker Compose configuration::

      ocs-registry:
        image: grumpy.physics.yale.edu/ocs-registry-agent:latest
        hostname: grumpy-docker
        volumes:
          - /home/user/ocs-site-configs/yale/prod/default.yaml:/config/default.yaml:ro
        depends_on:
          - "sisock-crossbar"

In the configuration a hostname must be defined that matches the hostname
configuration in your ocs-site-configs file. We suggest appending ``-docker``
to your current hostname. In our example our hostname is `grumpy`, so our
container hostname is `grumpy-docker`.

The ocs-site-configs directory needs to be mounted into the container so the
agent configuration can be read. We do this on the volumes line. The first path
will need to be modified for your system.

API
---

.. autoclass:: agents.registry.registry.Registry
    :members:
