.. highlight:: rst

.. _host_manager:

=================
HostManager Agent
=================

The HostManager Agent helps to manage the many Agent instances that
need to run on a single host machine, providing a way to start and
stop Agents without connecting to the host system.

For a complete discussion of this Agent and how to best use it, see
:ref:`centralized_management`.


.. argparse::
   :module: ocs.agents.host_manager.agent
   :func: make_parser
   :prog: agent.py



Configuration File Examples
---------------------------

Note that the HostManager Agent usually runs on the native system,
and not in a Docker container.  (If you did set up a HostManager in a
Docker container, it would only be able to start/stop agents within
that container.)

OCS Site Config
```````````````

Here's an example configuration block:

.. code-block:: yaml

     {'agent-class': 'HostManager',
      'instance-id': 'hm-mydaqhost1'}

By convention, the HostManager responsible for host ``<hostname>``
should be given instance-id ``hm-<hostname>``.


Description
-----------

Please see :ref:`centralized_management`.


Agent API
---------

.. autoclass:: ocs.agents.host_manager.agent.HostManager
    :members:

Supporting APIs
---------------

.. automethod:: ocs.agents.host_manager.agent.HostManager._reload_config
