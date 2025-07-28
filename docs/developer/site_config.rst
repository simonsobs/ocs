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
    For examples calling these commandline arguments see
    :ref:`ocs_agent_cmdline_examples`.
