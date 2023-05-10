.. highlight:: bash

.. _site_config_user:

======================
OCS Site Configuration
======================

Overview
========

This page describes the OCS configuration file. This file describes all the
Agents running in an observatory across all hosts.

.. _ocs_site_config_file:

OCS Site Config File
====================

The OCS Site Config File (SCF) is a single YAML file that defines connection
parameters for the crossbar server, as well as the Agents that will run on each
host, whether on the host system, or in a Docker container. The SCF may be
shared between multiple hosts, providing distinct configurations for each one.

Example Config
--------------
Here is an example of an SCF for a site with two hosts, and 4 agent
instances (running two different classes of agent):

.. code-block:: yaml

  hub:

    wamp_server: ws://10.10.10.3:8001/ws
    wamp_http: http://10.10.10.3:8001/call
    wamp_realm: test_realm
    address_root: observatory
    registry_agent: observatory.registry

  hosts:

    host-1: {

      # Directory for logs.
      'log-dir': '/simonsobs/log/ocs/',

      # List of additional paths to Agent plugin modules.
      'agent-paths': [
        '/simonsobs/ocs/agents/',
      ],

      # Description of host-1's Agents.
      # We have two readout devices; they are both Lakeshore 240. But they can
      # be distinguished, on startup, by a device serial number.

      'agent-instances': [
        {'agent-class': 'Lakeshore240Agent',
         'instance-id': 'thermo1',
         'arguments': [['--serial-number', 'LSA11AA'],
                       ['--mode', 'idle']]},
        {'agent-class': 'Lakeshore240Agent',
         'instance-id': 'thermo2',
         'arguments': [['--serial-number', 'LSA22BB'],
                       ['--mode', 'acq']]},
      ]
    }

    host-1-docker: {

      # Address of crossbar within Docker (based on service name)
      'wamp_server': 'ws://crossbar:8001/ws',
      'wamp_http': 'http://crossbar:8001/call',

      # Description of host-1's Agents running with Docker containers.
      # We have one readout device; a Lakeshore 372.

      'agent-instances': [
        {'agent-class': 'Lakeshore372Agent',
         'instance-id': 'LSARR00',
         'arguments': [['--serial-number', 'LSARR00'],
                       ['--ip-address', '10.10.10.55']]},
      ]
    }

    host-2: {

      # Crossbar start-up instructions (optional).
      'crossbar': {'config-dir': '/simonsobs/ocs/dot_crossbar/'},

      # Directory for logs.
      'log-dir': '/simonsobs/log/ocs/',

      # List of additional paths to Agent plugin modules.
      'agent-paths': [
        '/simonsobs/ocs/agents/',
      ],

      # Description of host-2's Agents.
      # We have two devices; another Lakeshore 240, and the OCS g3 file
      # Aggregator.

      'agent-instances': [
        {'agent-class': 'Lakeshore240Agent',
         'instance-id': 'thermo3',
         'arguments': [['--serial-number', 'LSA33CC'],
                       ['--mode', 'init']]},
        {'agent-class': 'AggregatorAgent',
         'instance-id': 'aggregator',
         'arguments': [['--initial-state', 'record'],
                       ['--time-per-file', '3600'],
                       ['--data-dir', '/data/']]},
      ]
    }

The `hub` section defines the connection parameters for the crossbar server.
This entire section will likely remain unchanged, except for the
``wamp_server`` and ``wamp_http`` IP addresses.

The `address_root` setting determines the leading token in all agent
and feed addresses on the crossbar network.  While "observatory" is
the default, it can be changed as long as the crossbar configuration
is also updated to permit operations on the `{address_root}.` uri.

Under `hosts` we have defined a three hosts, `host-1`, `host-1-docker`, and
`host-2`. This configuration example shows a mix of Agents running directly on
hosts and running within Docker containers.

.. note::
    The hostname within a Docker container is configurable in the
    ``docker-compose.yaml`` file. While you could configure it to be identical to
    the host system, we recommend naming the docker hosts with the convention
    "hostname"-"docker" to distinguish which Agents are running in Docker
    containers in the SCF.

.. note::
    To determine your host name, open a terminal and enter ``hostname``.

Each item under a given host describes the OCS Agents which can be run. For
example look at the first 372 Agent::

        {'agent-class': 'Lakeshore372Agent',
         'instance-id': 'LSARR00',
         'arguments': [['--serial-number', 'LSARR00'],
                       ['--ip-address', '10.10.10.55']]},

The ``agent-class`` is given by the actual Agent which will be running. This
must match the name defined in the Agent's code. The ``instance-id`` is a
unique name given to this agent instance. Here we use the Lakeshore 372 serial
number, `LSARR00`. Finally the arguments are used to pass default arguments to
the Agent at startup, which contains the serial number again as well as the IP
address of the 372.

.. _environment_setup:

Environment Setup
-----------------
By default the system will look for site files in the path pointed to
by environment variable ``OCS_CONFIG_DIR``. To define this, add the following
to your ``.bashrc`` file::

    export OCS_CONFIG_DIR='/path/to/ocs-site-configs/<your-institution-directory>/'

The default site filename is ``default.yaml``.  In practice, it is recommended
to name the configuration file after a given site, i.e. ``yale.yaml``, and symlink to
``default.yaml``::

    $ ln -s yale.yaml default.yaml

During development, multiple YAML files may be in active use; then users will
identify their config file through command line arguments when launching Agents
and Control Clients (see below).

.. note::
    If you're proceeding in the same terminal don't forget to source your
    ``.bashrc`` file.

Commandline Arguments
=====================
There are several built in commandline arguments that can be passed to Agents
when running. Agent Developers can also add custom arguments to their Agents.
If running an Agent directly on a host these can be thrown when running the
Agent manually, or configured in the 'arguments' section of your SCF. The built
in arguments for all Agents are listed here, followed by some examples.

.. note::
    OCS users deploying Agents within Docker containers should be aware that
    commandline options may be thrown by default within the Docker container. These
    can be overridden by a user within their `docker-compose.yaml` file using
    the CMD instruction.

.. argparse::
    :ref: ocs.site_config.add_arguments
    :prog:

.. _ocs_agent_cmdline_examples:

Examples
--------
In the following examples, consider the "LS240_agent.py", which implements an
Agent for talking to Lakeshore240 devices.  Suppose these are being run on a
host called "host-1".  Refer to the example site configuration listed above.
*(Note that to run these in the example tree you will usually need to add the
options that select the example SCF and host, namely:* ``--site-file
telescope.yaml --site-host host-1`` *. One exception to this is when using*
``--site=none``. *)*

1. Because there are two instances of "Lakeshore240Agent" registered
   in the SCF, we must somehow pick one when running the agent::

     $ python LS240_agent.py --instance-id=thermo1
     I am in charge of device with serial number: LSA11AA

2. We can ask our agent to connect to a different WAMP realm, for
   testing purposes (note this realm would need to be enabled in
   crossbar, probably)::

     $ python LS240_agent.py --instance-id=thermo1 --site-realm=my_other_realm
     I am in charge of device with serial number: LSA11AA

3. Run an instance of an Agent, but force all configuration matching
   to occur as though the Agent were running on a host called
   "host-2"::

     $ python LS240_agent.py --site-host=host-2
     I am in charge of device with serial number: LSA33CC

   Note that we do not need to specify an ``--instance-id``, because
   the SCF only lists one Lakeshore240Agent instance.

4. To avoid referring to a SCF at all, pass ``--site=none``.  Then
   specify enough information for the agent to connect and run::

     $ python LS240_agent.py --site=none \
     --site-hub ws://localhost:8001/ws --site-realm debug_realm \
     --address-root=observatory --instance-id=thermo1 \
     --serial-number=LSA11AA --mode=testing
     I am in charge of device with serial number: LSA11AA
