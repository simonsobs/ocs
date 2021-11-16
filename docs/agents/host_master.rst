.. highlight:: rst

.. _host_manager:

==================
Host Manager Agent
==================

The Host Manager Agent (HMA) helps to manage the many Agent instances
that need to run on a single host machine.  The HMA is [will be] able
to:

- Parse the entire site configuration file, and help to start, stop,
  and monitor each Agent instance running on a certain host.
- Integrate with systemd as a daemon, to allow the process to be
  controlled using standard systemctl commands, including how it
  behaves on system start up. 
- Accept control commands through the usual OCS channels, i.e. from
  anywhere in the network.

Direct user interaction with an HMA can be achieved through the 
``ocsbow`` command line script.

Configuration File Examples
---------------------------

The Host Manager Agent is an optional component.  In order to function
properly, it requires that site_config be in use.  It should be listed
in the SCF like other agents.  There should only be a single HMA per
host definition block.

OCS Site Config
```````````````

Here's an abbreviated SCF showing the correct configuration:

.. code-block:: yaml

  ...
  hosts:
    ...
    host-1: {
      ...
      'agent-instances': [
        ...
        {'agent-class': 'HostManager',
         'instance-id': 'hm-1',
         'arguments': []}
        ...
      ]
      ...
    }
    ...
  ...

The ``agent-class`` should be ``HostManager``.  The ``instance-id`` in
this example is based on a (recommended) convention that HostManager
live at ``hm-{host}``.

Agent API
---------

.. autoclass:: agents.host_manager.host_manager.HostManager
    :members:

Supporting APIs
---------------
.. automethod:: agents.host_manager.host_manager.HostManager._update_target_states
