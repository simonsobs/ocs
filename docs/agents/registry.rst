.. highlight:: rst

.. _registry:

Registry Agent
=======================

The registry agent is used to keep track of currently running active agents.
It listens to the heartbeat feeds of all agents on the crossbar server, 
and keeps track of the last heartbeat time of each agent and whether 
or not each agent has agent has "expired" (gone 5 seconds without a heartbeat).

This check happens in the registry's single "run" process. The session.data object
of this process is set to a dict of agents on the system, including their last 
heartbeat time, whether they have expired, and the time at which they expired.
This data can the be viewed by checking the session variable of the run process.

For instance, the following code will print agent's that have been on the system
since the registry started running::

    from ocs.matched_client import MatchedClient

    registry_client = MatchedClient('registry')
    status, msg, session = registry_client.run.status()

    print(session['data'])


Configuration
--------------------
To add the registry to your ocs setup, you can add this file to your site-config
yaml file::

    { 'agent-class': 'RegistryAgent',
      'instance-id': 'registry',
      'arguments': []},

Here is an example of a docker service that you can put in your docker-compose 
file to run the registry::

    ocs-registry:
        image: simonsobs/ocs-registry-agent:latest
        container_name: ocs-registry
        hostname: ocs-docker
        user: "9000"
        volumes: 
            - ${OCS_CONFIG_DIR}:/config

API
---

.. autoclass:: agents.registry.registry.Registry
    :members:
