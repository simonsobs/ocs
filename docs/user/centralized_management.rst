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


The main components of this system are:

- :ref:`host_manager` -- an instance of this Agent must be set up for
  each host or docker-ish host in the site_config.yaml file.
- ``systemd`` scripts -- there should be one systemd script (and
  launcher script) set up for each HostManager Agent instance; the
  command-line tool :ref:`install_systemd` helps with this.
- :ref:`ocsbow` -- the command-line client for communicating with
  HostManager Agents.


Setting up HostManager Agents
=============================


systemd Control of HostManagers
===============================

`systemd`_ is widely used on Linux systems to manage services and
daemons (and lots of other stuff).  The OCS script
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

  [ocs@ocs-host5 my-ocs]$ ocs-install-systemd --service-dir=.
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
`````````````````

The .service file is a `service_configuration_`<service configuration
file> for systemd, and there are lots of things that could be set up
in there.  The file created by ``ocs-install-systemd`` is minimal, but
sufficient.  It should look something like this::

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

.. _`service_configuration`: https://www.freedesktop.org/software/systemd/man/systemd.service.html

The launcher script
```````````````````

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
