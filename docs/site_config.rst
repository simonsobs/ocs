.. highlight:: bash

.. _site_config:

======================
OCS Site Configuration
======================

Overview
========

The purpose of ``ocs.site_config`` module is to help Agents and
Control Clients self-configure within a particular "site" context.  By
"site", we mean the set of instances of Agents and Clients, spread
across one or more hosts, that should form a single OCS network.

In an observatory or lab, it will be convenient if Agents and Clients
can determine the appropriate WAMP server and realm without user
intervention.  Furthermore, in cases where the same Agent code is
launched in multiple instances (to control distinct instances of the
same hardware model, for example) there needs to be a system that
assigns a WAMP base address (such as ``detlab.cryo.thermo2``) to
each Agent instance in a consistent matter.

The approach adopted here is that ``ocs.site_config`` works with
``ArgumentParser`` to both consume and then modify the arguments being
used to launch an Agent instance.  Roughly speaking, the following
occurs:

1. When launching an Agent, the user uses command line arguments to
   specify a site configuration file.  If no arguments are set, a
   sensible default is chosen.

2. The configuration file is parsed and the special configuration
   appropriate to this Agent instance is identified.  The
   configuration is determined based on the host the Agent instance is
   running on, and possibly by an "instance-id", which helps
   distinguish between independent Agents running from the same source
   script.

3. The special configuration parameters for this Agent instance are
   merged into the command line parameters.

4. Through normal processing of command line parameters in the Agent
   script, the appropriate WAMP connections, address registrations,
   and hardware associations are made.


OCS Site Config File
====================

The OCS Site Config File (SCF) will be a single YAML file.  The SCF
may be shared between multiple hosts, providing distinct
configurations for each one.

Here is an example of an SCF for a site with two hosts, and 4 agent
instances (running two different classes of agent):

.. code-block:: yaml

  hub:
  
    wamp_server: ws://host-2:8001/ws
    wamp_realm: detlab_realm
    address_root: detlab.cryo
    registry_agent: observatory.registry
  
  hosts:
  
    host-1: {
  
      # List of additional paths to Agent plugin modules.
      'agent-paths': [
        '/sobs/ocs/agents/',
      ],

      # Description of host-1's Agents?  We have two readout devices;
      # they are both Riverbank 320.  But they can be distinguished, on
      # startup, by a device serial number.
  
      'agent-instances': [
        {'agent-class': 'Riverbank320Agent',
         'instance-id': 'thermo1',
         'arguments': [['--serial-number', 'PX1204312'],
                       ['--mode', 'idle']]},
        {'agent-class': 'Riverbank320Agent',
         'instance-id': 'thermo2',
         'arguments': [['--serial-number', 'PX1204315'],
                       ['--mode', 'run']]},
      ]
    }
  
    host-2: {
  
      # List of additional paths to Agent plugin modules.
      'agent-paths': [
        '/sobs/ocs/agents/',
      ],

      # Description of host-2's Agents?  We have two devices: another
      # Riverbank 320, and a motor controller of some kind.
  
      'agent-instances': [
        {'agent-class': 'Riverbank320Agent',
         'instance-id': 'thermo3',
         'arguments': [['--serial-number', 'JM1212'],
                       ['--mode', 'run']]},
        {'agent-class': 'MotorControlAgent',
         'instance-id': 'motor4',
         },
      ]
    }

By default the system will look for site files in the path pointed to
by environment variable OCS_CONFIG_DIR.  The default site filename is
``default.yaml``.  In practice, users will set the environment
variable and create or symlink ``default.yaml`` with their site's
configuration.  During development, multiple YAML files may be in
active use; then users will identify their config file through command
line arguments when launching Agents and Control Clients (see below).


SiteConfig
----------

At root level, the configuration file should encode a SiteConfig
object.  The structure is described in the ``from_dict`` method of
the SiteConfig class:

.. autoclass:: ocs.site_config.SiteConfig
   :members: from_dict

The difference between a host name and a "pseudo-host name" is that a
host name might plausibly be computed automatically by calling
``socket.gethostname``, while a pseudo-host name is something the user
will have to specify explicitly (perhaps through the command line
argument ``--site-host``) when invoking the agent.

The ``hub`` information is used by all Agent and Control Clients to
connect to the OCS WAMP router.  This WAMP router (probably crossbar)
usually has its own configuration file.  The settings in SCF ``hub``
block are parsed by the ``from_dict`` method of the HubConfig class:

.. autoclass:: ocs.site_config.HubConfig
   :members: from_dict

HostConfig
----------

The structure of HostConfig encoding is described in the ``from_dict``
method of the HostConfig class:

.. autoclass:: ocs.site_config.HostConfig
   :members: from_dict

The significance of ``agent-paths`` is described more in :ref:`agent_plugins`.

InstanceConfig
--------------

The structure of InstanceConfig encoding is described in the
``from_dict`` method of the InstanceConfig class:

.. autoclass:: ocs.site_config.InstanceConfig
   :members: from_dict


Agent Site-related Command Line Parameters
==========================================

Agent code can connect to the ``ocs.site_config`` using the following
boilerplate code:

.. code-block:: python

  from ocs import site_config

  class MyHardwareDevice:
      # ...

  if __name__ == '__main__':
      # Get an ArgumentParser
      parser = site_config.add_arguments()

      # Add arguments that are specific to this Agent's function.
      pgroup = parser.add_argument_group('Agent Options')
      pgroup.add_argument('--serial-number')
      pgroup.add_argument('--mode')

      # Get the parser to process the command line.
      args = parser.parse_args()

      # Interpret options in the context of site_config.
      site_config.reparse_args(args, 'Riverbank320Agent')
      print('I am in charge of device with serial number: %s' % args.serial_number)
  
      # Call launcher function (initiates connection to appropriate
      # WAMP hub and realm).
      agent, runner = ocs_agent.init_site_agent(args)
  
      my_hd = MyHardwareDevice()
      #... register processes and tasks, e.g.:
      agent.register_process('acq', my_hd.start_acq, my_hd.stop_acq)

      runner.run(agent, auto_reconnect=True)


The call to ``site_config.reparse_args()`` will add a bunch of
arguments to the parser.  These can be used to select a particular
site configuration file, or to override site configuration entirely.

The command line options are described in the docstring for ``add_arguments``:

.. autofunction:: ocs.site_config.add_arguments()
   

Examples
--------

In the following examples, suppose we have "river_agent.py", which
implements an Agent for talking to Riverbank320 devices.  Suppose
these are being run on a host called "host-1".  Refer to the example
site configuration listed above.  *(Note that to run these in the
example tree you will usually need to add the options that select the
example SCF and host, namely:* ``--site-file telescope.yaml --site-host
host-1`` *. One exception to this is when using* ``--site=none``. *)*


1. Because there are two instances of "Riverbank320Agent" registered
   in the SCF, we must somehow pick one when running the agent::

     $ python river_agent.py --instance-id=thermo1
     I am in charge of device with serial number: PX1204312


2. We can ask our agent to connect to a different WAMP realm, for
   testing purposes (note this realm would need to be enabled in
   crossbar, probably)::

     $ python river_agent.py --instance-id=thermo1 --site-realm=my_other_realm
     I am in charge of device with serial number: PX1204312
   
3. Run an instance of an Agent, but force all configuration matching
   to occur as though the Agent were running on a host called
   "host-2"::

     $ python river_agent.py --site-host=host-2
     I am in charge of device with serial number: JM1212

   Note that we do not need to specify an ``--instance-id``, because
   the SCF only lists one Riverbank320Agent instance.

4. To avoid referring to a SCF at all, pass ``--site=none``.  Then
   specify enough information for the agent to connect and run::

     $ python river_agent.py --site=none \
     --site-hub ws://localhost:8001/ws --site-realm debug_realm \
     --address-root=observatory --instance-id=thermo1 \
     --serial-number=PX1204312 --mode=testing
     I am in charge of device with serial number: PX1204312


Control Clients and the Site Config
===================================

As of this writing, Control Clients do not store configuration in the
SCF.  But there is an interim interface available for Control Clients
to access the Site Configuration, with the usual command-line
overrides.  Control Clients that use the ``run_control_script``
function to launch can instead use ``run_control_script2``, which
behaves as follows:

.. autofunction:: ocs.client_t.run_control_script2


The control client script might look something like this (see also
river_ctrl.py in the examples):  
    
.. code-block:: python

  def my_script(app, pargs):
      from ocs import client_t

      # We've added a --target option.
      # Construct the full agent address.
      agent_addr = '%s.%s' % (pargs.address_root, pargs.target)
  
      # Create a ProcessClient for the process 'acq'.
      cw = client_t.ProcessClient(app, agent_addr, 'acq')
  
      print('Starting a data acquisition process...')
      d1 = yield cw.start()
      #...


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


.. _agent_plugins:

Agent Script Discovery
----------------------

Agent scripts are currently written as stand-alone python scripts (and
thus not not importable through the main ``ocs`` python module).  To
support automatic launching of Agents, ``site_config`` includes a
plugin-style system to register Agent scripts.  This is flexible
enough to support both the natively packaged Agents and any
"third-party" agents needed in a particular installation.  The system
works like this:

- A bundle of Agent scripts is assembled at some location.  There are
  no restrictions on where these scripts can live in the file system.
  For example, a script called ``riverbank_agent.py`` might live in
  ``/sobs/agents/``.
- A special "registration script" is written, with a filename of the
  form ``ocs_plugin_*.py``.  This script should live in Python's
  import path, or else (and this is better), the path to the script
  should be included in the ``agent-paths`` variable in the SCF for
  this host.  For example, we might put the file in ``/sob/agents``
  and call it ``ocs_plugin_sobs.py``.
- When the site_config system (specifically the HostMaster agent)
  needs to find a particular agent script, it:
  - Adds any directories in ``agent-paths`` to the Python import path.
  - Scans through all importable modules, and imports them if they
    match the ``ocs_plugin_*`` name pattern.
- The ``ocs_plugin`` script makes calls into ocs to associate a
  particular script filenames to agent class names.  In our example,
  ``ocs_plugin_sobs.py`` would call
  ``ocs.site_config.register_agent_class('RiverBank',
  '/sobs/agents/riverbank_agent.py')``.

A good example of a plugin script can be found in the OCS agents
directory, ``ocs_plugins_standard.py``.


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


ocsbow (Host Master / site_config command line tool)
----------------------------------------------------

(The output from ``ocsbow --help`` should be rendered here.)

.. argparse::
   :module: ocs.ocsbow
   :func: get_parser
   :prog: ocsbow



Systemd Integration [empty]
---------------------------

