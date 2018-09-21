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
instances (running two different classes of agent)::

  hub:
  
    wamp_server: ws://host-2:8001/ws
    wamp_realm: detlab_realm
    address_root: detlab.cryo
  
  hosts:
  
    host-1: {
  
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
``default.yaml``.  In practice, users launching an Agent or Control
Client select the site name or give the complete site config filename
through the command line (see below).

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

The structure of HostConfig encoding is described in the ``from_dict``
method of the HostConfig class:

.. autoclass:: ocs.site_config.HostConfig
   :members: from_dict


The structure of InstanceConfig encoding is described in the
``from_dict`` method of the InstanceConfig class:

.. autoclass:: ocs.site_config.InstanceConfig
   :members: from_dict



Agent Site-related Command Line Parameters
==========================================

Agent code can connect to the ``ocs.site_config`` using the following
boilerplate code::

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



OCS Host Manager Agent
======================

There's nothing in the rulebook that says we can't use OCS Agents to
restart OCS Agents.  It would be particularly useful to have an Agent
that is in charge of starting, stopping, and monitoring all agent
instances that are running on a single host.

.. todo:: Create this Agent, and explain how to use it.

