.. _systemd_config:

=====================
systemd Configuration
=====================

Overview
========

In distributed OCS systems involving multiple hosts, it is often desirable that:

- the OCS Agents can be started and stopped from some central host
  (including the limit of bringing down all Agents, across the system,
  without having to connect to multiple hosts).
- the OCS Agents start up, automatically, if the computer is
  restarted.

The first capability is addressed by ocsbow and the HostMaster Agent.
In order that the HostMaster starts up automatically on reboot, we can
use systemd; that is what this section talks about.

Installing the systemd service
==============================

.. note::

   Before bothering with systemd, you must already have ocs installed
   on the host in question, with the site config specified for this
   host and a HostMaster instance properly configured to control
   agents on the system.

The script ``ocs-install-systemd`` assists with generating the
necessary wrapper script and the systemd service configuration file.

To generate the files, run::

  [ocs@ocs-host5 my-ocs]$ ocs-install-systemd --service-dir=.
  Writing /home/ocs/ocs-site-configs/my-ocs/launcher-hostmaster-ocs-host5.sh ...
  Writing ./ocs-hostmaster.service ...

After generating the service file, copy it to the systemd folder::

  $ sudo cp ocs-hostmaster.service /etc/systemd/system/

At this point you should be able to check the "status" of the
service::

  $ sudo systemctl status ocs-hostmaster.service

It probably won't say very much.  If you've updated the service file
recently (i.e. reinstalled it, with or without changes), it might
recommend that you run ``systemctl daemon-reload``; you should
probably do so.

Starting and stopping the service
=================================

Use standard systemctl::

  $ sudo systemctl start ocs-hostmaster.service
  $ sudo systemctl stop ocs-hostmaster.service

Getting the service to start on boot
====================================

The systemd terminology for "will start on boot" is "enabled"::

  $ sudo systemctl enable ocs-hostmaster.service

And to turn off start-on-boot::

  $ sudo systemctl disable ocs-hostmaster.service

To debug any issues with the HostMaster not starting, inspect the
limited made avialable through ``systemctl status``, and if need be
add some logging to the launcher script.

The service file
================

The service file is given a generic name, "ocs-hostmaster.service", by
default, with the expectation that a single host will probably only
need to have a single HostMaster.

You might want to edit the file to change the user under which the
HostMaster will run, or other systemd parameters (such as how
persistently the system should try to restart the Agent).  Some of
that can be set by passing certain options to ``ocs-install-systemd``;
some will just need to be manually added (before or after it is
installed on the system).

If you want to keep copies of the service file in version control, be
aware that it might make sense to call the service
"ocs-hostmaster.service" on each system, but you will need different
filenames (probably ocs-hostmaster-<hostname>.service) in your site
config dir.

The launcher script
===================

The launcher script is (usally) a bash script that runs HostMaster.
It is intended for this to live in the OCS configuration directory
(near the site config file), so it can be version controlled more
easily.  If special environment (such as conda configuration) needs to
be set up before launching the HostMaster, you can add it to this
script.  But it might just work fine with the defaults.

