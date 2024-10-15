.. _crossbar_config_user:

======================
Crossbar Configuration
======================

Overview
========

This page describes the crossbar server configuration file. This file defines
the interface to the crossbar server.

.. note::

    For most simple lab deployments of OCS, you should not need to modify this
    file and can use the one that comes with the ``simonsobs/ocs-crossbar``
    Docker Image.

Configuration File Template
---------------------------
The template that the default OCS crossbar config is built with is shown here:

.. literalinclude:: ../../docker/crossbar/config.json.template

The variables `realm`, `address_root`, and `port` are all configurable and must
match configuration options set in your SCF. Keep reading this page to see how
to configure these variables.

.. note::
    Changing the `address_root` has implications for the how your data is
    stored and accessed in tools such as Grafana. It is recommended you pick
    something reasonable when you first configure your system and do not change it
    later.

For further details on crossbar server configuration, see the crossbar `Router
Configuration`_ page.

.. _`Router Configuration`: https://crossbar.io/docs/Router-Configuration/

Running with Docker
===================

We recommend running crossbar within a Docker container. We build the
``simonsobs/ocs-crossbar`` container from the official `crossbar.io Docker
image`_, specifically the cpy3 version. Bundled within the container is a
simple crossbar configuration file template with defaults that are
compatible with examples in this documentation.

To adjust the crossbar configuration in the container, you can either:

- Use environment variables to alter the most basic settings
- Generate and mount a new configuration file over
  ``/ocs/.crossbar/config.json`` with the proper permissions

.. _`crossbar.io Docker image`: https://hub.docker.com/r/crossbario/crossbar

Environment variables in ocs-crossbar
-------------------------------------
The following environment variables can be set, to affect the
generation of the crossbar configuration file when the container
starts up:

- OCS_ADDRESS_ROOT (default "observatory"): the base URI for OCS
  entities (this needs to match the `address_root` set in the SCF).
- OCS_CROSSBAR_REALM (default "test_realm"): the WAMP realm to
  configure for OCS.
- OCS_CROSSBAR_PORT (default 8001): the port on which crossbar will
  accept requests.

Here is an example of a docker compose entry that overrides the
OCS_ADDRESS_ROOT::

      crossbar:
        image: simonsobs/ocs-crossbar:latest
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        environment:
          - PYTHONUNBUFFERED=1
          - OCS_ADDRESS_ROOT=laboratory

Bind Mounting the Configuration
-------------------------------
To instead mount a new configuration into the pre-built image, first chown
your file to be owned by user and group 242 (the default crossbar UID/GID),
then mount it appropriately in your docker compose file. Here we assume you
put the configuration in the directory ``./dot_crossbar/``::

    $ chown -R 242:242 dot_crossbar/

.. note::
    If you do not already have a configuration file to modify and use, see the
    next section on generating one.

Your docker compose service should then be configured like::

    crossbar:
      image: simonsobs/ocs-crossbar
      ports:
        - "8001:8001" # expose for OCS
      volumes:
        - ./dot_crossbar:/ocs/.crossbar
      environment:
        - PYTHONUNBUFFERED=1

Generating a New Config File
----------------------------
``ocs-local-support`` can be used to generate a default configuration
file, based on options in your SCF, which can then be modified if
needed.

First, we make sure our ``OCS_CONFIG_DIR`` environment variable is set::

    $ cd ocs-site-configs/
    $ export OCS_CONFIG_DIR=`pwd`

We should make a directory for the crossbar config, following along above let's
call it ``dot_crossbar/`` (typically a dot directory, but for visibility we'll
avoid that)::

    $ mkdir -p ocs-site-configs/dot_crossbar/

This directory needs to be configured as your crossbar 'config-dir' in your
ocs-site-config file. (See example in :ref:`site_config_user`.) Now we can
generate the config::

    $ ocs-local-support generate_crossbar_config
    The crossbar config-dir is set to:
      ./dot_crossbar/
    Using
      ./dot_crossbar/config.json
    as the target output file.

    Generating crossbar config text.
    Wrote ./dot_crossbar/config.json

You should now see a crossbar config file in ``./dot_crossbar/``. Make any
modifications needed for your deployment.

.. note::

    The crossbar 'config-dir' block and the 'agent-instance' block
    defining the 'HostManager' Agent are both required for the system
    you are running `ocs-local-support` on. Be sure to add these to
    your SCF if they do not exist.
