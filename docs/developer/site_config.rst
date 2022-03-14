.. highlight:: bash

.. _site_config_dev:

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

ocs.site_config
===============
This section documents in detail the classes in `ocs.site_config`. For details
about the site configuration file, please refer to :ref:`ocs_site_config_file`.

SiteConfig
----------
At root level, the configuration file should encode a SiteConfig
object. The structure is described in the ``from_dict`` method of
the SiteConfig class:

.. autoclass:: ocs.site_config.SiteConfig
    :members: from_dict
    :noindex:

The ``hub`` information is used by all Agent and Control Clients, on
all hosts, to connect to the OCS WAMP router.  This WAMP router
(probably crossbar) usually has its own configuration file.  The
settings in SCF ``hub`` block are parsed by the ``from_dict`` method
of the HubConfig class:

.. autoclass:: ocs.site_config.HubConfig
    :members: from_dict
    :noindex:

HostConfig
----------

The structure of HostConfig encoding is described in the ``from_dict``
method of the HostConfig class:

.. autoclass:: ocs.site_config.HostConfig
    :members: from_dict
    :noindex:

To allow ocs to manipulate the ``crossbar`` router (e.g. if you want
to easily start and stop it using ``ocsbow``), then the ``crossbar``
variable should be defined, with (at least) an empty dictionary.  The
details of the options are described in the ``from_dict`` method of
the CrossbarConfig class:

.. autoclass:: ocs.site_config.CrossbarConfig
    :members: from_dict
    :noindex:

The significance of ``agent-paths`` is described more in
:ref:`agent_plugins`.

InstanceConfig
--------------

The structure of InstanceConfig encoding is described in the
``from_dict`` method of the InstanceConfig class:

.. autoclass:: ocs.site_config.InstanceConfig
    :members: from_dict
    :noindex:

.. _parse_args:

Agent Site-related Command Line Parameters
==========================================

Agent code can connect to the ``ocs.site_config`` using the following
boilerplate code:

.. code-block:: python

  from ocs import site_config

  class MyHardwareDevice:
      # ...

  def make_parser(parser=None):
      if parser is None:
          parser = argparse.ArgumentParser()

      pgroup = parser.add_argument_group('Agent Options))
      pgroup.add_argument("--serial-number", help="Serial number of device")
      pgroup.add_argument("--mode", default="idle", choices=['idle', 'acq'])
      pgroup.add_argument('--num-channels', default=2, type=int,
                          help='Number of fake readout channels to produce. '
                          'Channels are co-sampled.')
      pgroup.add_argument('--sample-rate', default=9.5, type=float,
                          help='Frequency at which to produce data.')

  if __name__ == '__main__':

      parser = make_parser()
      args = site_config.parse_args(agent_class='FakeDataAgent', parser=parser)

      print('I am in charge of device with serial number: %s' % args.serial_number)
  
      # Call launcher function (initiates connection to appropriate
      # WAMP hub and realm).
      agent, runner = ocs_agent.init_site_agent(args)
  
      my_hd = MyHardwareDevice()
      #... register processes and tasks, e.g.:
      agent.register_process('acq', my_hd.start_acq, my_hd.stop_acq)

      runner.run(agent, auto_reconnect=True)


The call to ``site_config.parse_args()`` will first pre-parse any command line
arguments to determine the correct site, host, and instance to use for the
specified agent_class. It will then merge any specified command line arguments
with the instance arguments specified in the site-config file, and parse them
with the full agent + site parser, so the returned namespace will contain
additional site-info settable from the site's parser.

.. argparse::
    :ref: ocs.site_config.add_arguments
    :prog:

.. note::
    This is slightly different from the older way of parsing arguments with
    ``reparse_args``, but should return the same namespace. The only difference is that
    the new version parses all arguments with the argparse parser, so you can be sure
    that defaults and type specifications will apply.

    To change to the newer version, just make sure you define the agent parser
    first, and pass it to the parse_args function as shown in the example above.

.. note::
    For examples calling these commandline arguments see
    :ref:`ocs_agent_cmdline_examples`.


Control Clients and the Site Config
===================================

As of this writing, Control Clients do not store configuration in the
SCF.  But there is an interim interface available for Control Clients
to access the Site Configuration, with the usual command-line
overrides.  Control Clients that use the ``run_control_script``
function to launch can instead use ``run_control_script2``, which
behaves as follows:

.. autofunction:: ocs.client_t.run_control_script2
    :noindex:

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


.. _agent_plugins:

Agent Script Discovery
======================

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
  ``/simonsobs/agents/``.
- A special "registration script" is written, with a filename of the
  form ``ocs_plugin_*.py``.  This script should live in Python's
  import path, or else (and this is better), the path to the script
  should be included in the ``agent-paths`` variable in the SCF for
  this host.  For example, we might put the file in ``/simonsobs/agents``
  and call it ``ocs_plugin_simonsobs.py``.
- When the site_config system (specifically the HostManager agent)
  needs to find a particular agent script, it:

  - Adds any directories in ``agent-paths`` to the Python import path.
  - Scans through all importable modules, and imports them if they
    match the ``ocs_plugin_*`` name pattern.

- The ``ocs_plugin`` script makes calls into ocs to associate a
  particular script filenames to agent class names.  In our example,
  ``ocs_plugin_simonsobs.py`` would call
  ``ocs.site_config.register_agent_class('RiverBank',
  '/simonsobs/agents/riverbank_agent.py')``.

A good example of a plugin script can be found in the OCS agents
directory, ``ocs_plugins_standard.py``.
