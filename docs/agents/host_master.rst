.. highlight:: rst

.. _host_master:

================
HostMaster Agent
================

The HostMaster Agent (HMA) helps to manage the many Agent instances
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

Agent Configuration
-------------------

The Host Master Agent is an optional component.  In order to function
properly, it requires that site_config be in use.  It should be listed
in the SCF like other agents.  There should only be a single HMA per
host definition block.

Here's an abbreviated SCF showing the correct configuration:

.. code-block:: yaml

  ...
  hosts:
    ...
    host-1: {
      ...
      'agent-instances': [
        ...
        {'agent-class': 'HostMaster',
         'instance-id': 'master-host-1',
         'arguments': []}
        ...
      ]
      ...
    }
    ...
  ...

The ``agent-class`` should be ``HostMaster``.  The ``instance-id`` in
this example is based on a (recommended) convention that HostMaster
live at ``master-{host}``.

API
---

.. autoclass:: agents.host_master.host_master.HostMaster
    :members: master_process, master_process_stop, update_task, die
