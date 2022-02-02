.. _centralized_management:

======================
Centralized Management
======================

Overview
========

In a distributed OCS involving multiple hosts, it is advantageous to
have a way to start and stop Agents without ssh-ing to the various
host systems.

The HostManager Agent and ocsbow CLI script provide a way to do this.
When fully configured, the system provides the following
functionality:

- Any OCS Agent in the system can be started and stopped from a single
  client.  This includes support for bringing down all Agents, across
  the system, without having to connect to multiple hosts.
- The OCS Agents running on a particular system will start up
  automatically when the system is booted (even if the Agents are not
  contained in Docker containers).
- The basic health of Agents, across the system, can be monitored and
  individual agents restarted using HostManager panels in OCS web.


.. warning::

    The HostManager system, once in place, should be the only means by
    which those managed Agents are started or stopped.  For Agents
    running on the native OS, HostManager will run them as child
    processes so that it can monitor their states more easily.  For
    Agents running in docker containers, HostManager takes charge of
    the implicated containers and there will be conflicts if users
    also try to use ``docker-compose`` to restart containers.

The main components of this system are:

- :ref:`host_manager` -- an instance of this Agent must be set up for
  each host or docker-ish host in the site_config.yaml file.
- ``systemd`` scripts -- there should be one systemd script (and
  launcher script) set up for each HostManager Agent instance; the
  command-line tool :ref:`ocs-install-systemd` helps with this.
- :ref:`ocsbow` -- the command-line client for communicating with
  HostManager Agents.



Configuration of HostManager Agents
===================================

The HostManager Agents will normally run on the bare systems, rather
than in Docker containers.  This is because they need to start and
stop other processes and start Docker containers on the system.

To enable full centralized control of your system, there must be an
instance of HostManager Agent set up for each host in the Site Config
file (SCF).  Some hosts in the SCF describe agents running in Docker
containers, and normally these are grouped to correspond to a single
docker-compose.yaml file.  Each such host needs a HostManager set up,
though the HostManager runs on the native system and not in a docker
container.

Config for native system hosts
------------------------------

Considering the Example Config from :ref:`ocs_site_config_file`, the
SCF there has 3 hosts defined: ``host-1``, ``host-1-docker``, and
``host-2``.  We must add a HostManager block to the
``'agent-instances'`` list in each case.  For example, the ``host-1``
block would become:

.. code-block:: yaml

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
      # We also have a HostManager.

      'agent-instances': [
        {'agent-class': 'Lakeshore240Agent',
         'instance-id': 'thermo1',
         'arguments': [['--serial-number', 'LSA11AA'],
                       ['--mode', 'idle']]},
        {'agent-class': 'Lakeshore240Agent',
         'instance-id': 'thermo2',
         'arguments': [['--serial-number', 'LSA22BB'],
                       ['--mode', 'acq']]},
        {'agent-class': 'HostManager',
         'instance-id': 'hm-host-1',
         'arguments': [['--initial-state', 'up']],
        },
      ]
    }

To test the configuration, you can try to launch the HostManager.  In
a fully configured system, this will be done through systemd.  But for
initial setup you can use the ``ocs-local-support`` program.

.. note::
   When you launch HostManager, it will try to start new processes for
   each of its managed Agents!  So you should shut down any running
   instances, and be in a state where it's acceptable to start up new
   instances.


To launch the HostManager agent for the system you're logged into, run::

  $ ocs-local-support start agent --foreground

You can Ctrl-C out of this to kill the agent.  (If you accidentally
run this without the ``--foreground``, you can try using
``ocs-local-support stop agent`` to stop it.)

To start using ocsbow to communicate with this HostManager, see
`Communicating with HostManager Agents`_.  To set the HostManager
up in systemd (useful especially to have the HostManager and managed
agents start up when the system boots), see `systemd Control of
HostManagers`_.


Config for docker pseudo-hosts
------------------------------

Considering the Example Config from :ref:`ocs_site_config_file`, the
host ``host-1-docker`` describes agents that are launched in
containers using ``docker-compose``.  However, instead of adding a
HostManager to that host block, we simply add a pointer to the
relevant docker-compose.yaml file in the HostManager arguments in
``host-1``; the new config for the HostManager would be:

.. code-block:: yaml

    host-1: {
      ...
      'agent-instances': [
      ...
        {'agent-class': 'HostManager',
         'instance-id': 'hm-host-1',
         'arguments': [['--initial-state', 'up'],
                       ['--docker-compose', '/home/ocs/site-config/host-1-docker/docker-compose.yaml']]},
      ]
    }

After adding the ``--docker-compose`` argument to the site config,
restart HostManager; changes to the command line parameters can't be
processed without restarting the Agent.

.. note::

   The HostManager process must be running as a user with sufficient
   privileges to run ``docker`` and ``docker-compose``.  Usually that
   means that the user must be root, or must be in the "docker" user
   group.  The recommendation is that you add the :ref:`OCS user
   <create_ocs_user>` to the docker group (see
   `docker-linux-postinstall`_).

.. _docker-linux-postinstall: https://docs.docker.com/engine/install/linux-postinstall/

The HostManager will now keep track of the agents listed under host-1,
and also the services defined in that docker-compose.yaml file.  In
``ocsbow`` and OCS Web (see below) the Agents will be listed by their
instance-id, but the docker containers will be listed by their service
name.  So you should probably make the service name correspond to
(perhaps a slight modification of) the instance_id.

.. note::

   The HostManager does not try to figure out which services in the
   ``docker-compose.yaml`` are running Agents and which ones aren't.
   All services defined in the docker-compose.yaml file will be
   treated the same way, and made available for monitoring and control
   by clients.


Advanced host config
~~~~~~~~~~~~~~~~~~~~

In some cases you might want to temporarily exclude an agent from
HostManager control.  You can do this by setting ``'manage':
'no'``.  This only works for Agents running on the native system.


Communicating with HostManager Agents
=====================================

This section describes using the :ref:`ocsbow` command line tool to
communicate with all the HostManager agents in an OCS setup.  A
complementary approach is to use OCS Web; see `Using OCS Web with HostManager`_.

``ocsbow`` is a special client program that knows how to parse the SCF
and figure out what HostManager are running on the system.  This
allows it to query each one (using standard OCS techniques) and
present the status of all the managed agents.

Like any other OCS client program, ``ocsbow`` needs to be able to find
the site config file.  (If you have just made changes to the SCF to
add HostManager agents, make sure the system you're running this
client on also has access to that updated SCF.)


Inspecting status
-----------------

The basic status display is shown if you run ``ocsbow``.  In the
example above, the output will look something like this::

  $ ocsbow
  ocs status
  ----------

  The site config file is :
    /home/ocs/site-config/default.yaml

  The crossbar base url is :
    http://my-crossbar-server:8001/call

  ---------------------------------------------------------------------------
  Host: host-1

    [instance-id]                  [agent-class]           [state]   [target]
    hm-host-1                      HostManager                  up        n/a
    thermo1                        Lakeshore240Agent            up         up
    thermo2                        Lakeshore240Agent            up         up
    ocs-LSARR00                    docker                       up         up

  ---------------------------------------------------------------------------
  Host: host-2

    [instance-id]                  [agent-class]           [state]   [target]
    hm-host-2                      HostManager                  up        n/a
    thermo3                        Lakeshore240Agent            up         up
    aggregator                     AggregatorAgent              up         up


The output is interpreted as follows.  After an initial statement of
what site config file is being used, and the crossbar access address,
a block is presented for each host in the SCF.  Within each host
block, each agent instance-id is listed, along with its agent-class
and values for "state" and "target".

Note that if an Agent has been configured with ``'manage': 'no'`` or
``'manage': 'docker'``, then it will show question marks in the state
and target fields, e.g.::

    [instance-id]                  [agent-class]           [state]   [target]
    LSARR00                        Lakeshore372Agent             ?          ?


``state`` and ``target``
~~~~~~~~~~~~~~~~~~~~~~~~

The ``state`` column shows whether the Agent is currently running
(``up``) or not (``down``).  This column may also show the value
``unstable``, which indicates that an Agent keeps restarting (this
usually indicates a code, configuration, or hardware error that is
causing the agent to crash shortly after start-up).

For the non-HostManager agents, the ``target`` column shows the state
that HostManager will try to achieve for that Agent.  So if
``target=up`` then the HostManager will start the Agent, and keep
restarting the Agent if it crashes or otherwise terminates.  If
``target=down`` then the HostManager will stop the Agent and not
restart it.  (Note that in the case of Agents in docker containers,
the HostManager will use docker and docker-compose to monitor the
state of containers, and request start or stop in order to match the
target state.)

Each HostManager can be commanded to change the target state of Agents
it controls; see `Start/Stop Agents`_.

For the HostManager lines, the ``target`` will always be ``[n/a]`` and
the state will either be ``up``, ``down``, or ``sleeping``.  When the
HostManager appears to be functioning normally, the state will be
``up``.  If the HostManager appears to not be running at all, the
state will be ``down``.  If the HostManager is running but the
"manage" Process is not running for some reason, the state will be
``sleeping``.


Start/Stop Agents
-----------------

To start an Agent, through its HostManager, run ``ocsbow up``,
specifying the agent-id.  For example::

  $ ocsbow up thermo1

The correct HostManager will be contacted and ``target=up`` will be
set for that Agent instance.  Similarly::

  $ ocsbow down thermo1

will set ``target=down`` for the ``thermo1`` instance.


.. note::
   When using ocsbow to control Docker-based agents, remember to use
   the service name (i.e. ``ocs-LSARR00`` in the example above) rather
   than the instance-id (``LSARR00``).



Start/Stop Batches of Agents
----------------------------

You can pass multiple instance-id targets in a single line, even if they are managed by
different HostManagers.  For example::

  $ ocsbow down thermo1 thermo3

If you pass the instance-id of a *HostManager*, then the target state
will be applied to *all* its managed agents.  So in our example::

  $ ocsbow down hm-host-1

is equivalent to::

  $ ocsbow down thermo1 thermo2

You can target *all* the managed agents in a system using the ``-a``
(``--all``) switch::

  $ ocsbow down -a    # Bring down all the agents!
  $ ocsbow up -a      # Bring up all the agents!


Note that none of these commands will cause the HostManager agents to
stop.  Restarting HostManagers must be done through another means (the
systemd controls, or ``ocs-local-support``).


systemd Control of HostManagers
===============================

`systemd`_ is widely used on Linux systems to manage services and
daemons (and lots of other stuff).  The OCS program
:ref:`ocs-install-systemd` may be used to help register each
HostManager Agent as a systemd service.  The `systemctl`_ program
(part of systemd) can then be used to start and stop the Agent, or to
configure it to start automatically on system boot.

.. note::

   Before bothering with systemd, you must already have ocs installed
   on the host in question, with the site config specified for this
   host and a HostManager instance properly configured to control
   agents on the system.

.. _`systemd`: https://systemd.io/
.. _`systemctl`: https://man7.org/linux/man-pages/man1/systemctl.1.html

Configuring the systemd service
-------------------------------

The service configuration consists of two files, which are described
in more detail a little later:

- The *.service file*
- The *launcher script*

To generate those files, run::

  $ hostname
  ocs-host5
  $ cd $OCS_CONFIG_DIR
  $ ocs-install-systemd --service-dir=.
  Writing /home/ocs/ocs-site-configs/my-ocs/launcher-hostmanager-ocs-host5.sh ...
  Writing ./ocs-hostmanager.service ...

After generating the .service file, copy it to the systemd folder::

  $ sudo cp ocs-hostmanager.service /etc/systemd/system/

At this point you should be able to check the "status" of the
service::

  $ sudo systemctl status ocs-hostmanager.service

It probably won't say very much.  If you've updated the service file
recently (i.e. reinstalled it, with or without changes), it might
recommend that you run ``systemctl daemon-reload``; you should
probably do so.

At this point you might want to jump to :ref:`controlling_systemd`.
Some additional details about the service file and launcher script are
provided here.

The .service file
~~~~~~~~~~~~~~~~~

The .service file is a `service configuration file`_ for systemd, and
there are lots of things that could be set up in there.  The file
created by :ref:`ocs-install-systemd` is minimal, but sufficient.  It
should look something like this::

  [Unit]
  Description=OCS HostManager for server5

  [Service]
  ExecStart=/home/ocs/git/ocs-site-configs/my-lab/launcher-hm-server5.sh
  User=ocs
  Restart=always

  [Install]
  WantedBy=multi-user.target


This can be edited further before (or after) it is installed.  You can
control the hostname (server5 here) and system user (ocs here) that
get dropped into the template with the ``--service-host`` and
``--service-user`` arguments to ``ocs-install-systemd``... or just
edit them by hand.

If you want to keep copies of the service file in version control, be
aware that it might make sense to call the installed service file
``ocs-hostmanager.service``, on each system, but you will need
different filenames (probably ``ocs-hostmanager-<hostname>.service``)
in your site config dir.

.. _`service configuration file`: https://www.freedesktop.org/software/systemd/man/systemd.service.html

The launcher script
~~~~~~~~~~~~~~~~~~~

The launcher script is a bash script that runs HostManager.  It is
called by systemd when starting the service.  Any environment
variables or additional command line arguments that need to be set for
the HostManager instance can be set in this script.  The script should
normally be kept with other OCS configuration files, such as the
SCF.

The launcher script is probably not needed, because a lot of
additional configuration (such as environment variables) can be put
into a .service file.  But in the interest of familiarity, the default
behavior provides users with the launcher script.


.. _controlling_systemd:

Controlling the systemd service
-------------------------------

The usual systemctl commands (start, stop, restart, enable, disable)
are used to control the service.


**Starting and stopping the service:**

Use the usual systemctl commands to start ...::

  $ sudo systemctl start ocs-hostmanager.service

... or to stop the service::

  $ sudo systemctl stop ocs-hostmanager.service


**Checking status**

The status of the service (including whether it is running, whether it
is enabled, and a few lines from the logs) can be obtained from the
"status" command to systemctl::

  $ sudo systemctl status ocs-hostmanager.service


**Controlling startup on boot**

The systemd terminology for "will be launched when system boots" is
"enabled".  To enable launch-on-boot::

  $ sudo systemctl enable ocs-hostmanager.service

To disable launch-on-boot::

  $ sudo systemctl disable ocs-hostmanager.service


Using OCS Web with HostManager
==============================

The OCS Web system includes a Panel for HostManager agents.  Here's a
screenshot of what that looks like:

.. image:: ../_static/ocs_web_hostmanager.png

In its current form, the control panel is associated with a single
HostManager, and there is no way to broadcast target state requests to
multiple targets.
