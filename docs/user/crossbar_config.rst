.. _crossbar_config_user:

======================
Crossbar Configuration
======================

Overview
========

This page describes the crossbar server configuration file. This file defines
the interface to the crossbar server.

.. note::

    For most test deployments of OCS, you should not need to modify this file
    and can use the one that comes with the ``simonsobs/ocs-crossbar`` Docker
    Image.

Example Config
--------------
An example of the default OCS crossbar config that is bundled into
``simonsobs/ocs-crossbar`` can be found in the repository at
`ocs/docker/crossbar/config.json`_. This is based on the template in
`ocs/ocs/support/crossbar_config.json`_.

The unique parts of this to OCS are the realm name, "test_realm", defined
roles of "iocs_agent" and "iocs_controller, and "address_root" of
"observatory.". Additionally, we run on port 8001.

For further details on crossbar server configuration, see the crossbar `Router
Configuration`_ page.

.. _`ocs/docker/crossbar/config.json`: https://github.com/simonsobs/ocs/blob/develop/docker/crossbar/config.json
.. _`ocs/ocs/support/crossbar_config.json`: https://github.com/simonsobs/ocs/blob/develop/ocs/support/crossbar_config.json
.. _`Router Configuration`: https://crossbar.io/docs/Router-Configuration/

Generating a New Config File
----------------------------
``ocsbow`` can be used to generate a default configuation file, based on
options in your OSC file, which can then be modified if needed.

First, we make sure our ``OCS_CONFIG_DIR`` environment variable is set::

    $ cd ocs-site-configs/
    $ export OCS_CONFIG_DIR=`pwd`

We should make a directory for the crossbar config, let's call it
``dot_crossbar/`` (typically a dot directory, but for visilibity we'll avoid
that)::

    $ mkdir -p ocs-site-configs/dot_crossbar/

This directory needs to be configured as your crossbar 'config-dir' in your
ocs-site-config file. Now we can generate the config::

    $ ocsbow crossbar generate_config
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
    The crossbar 'config-dir' block and the 'agent-instance' block defining the
    'HostMaster' Agent are both required for the system you are running ocsbow on.
    Be sure to add these to your SCF if they do not exist.

Running with Docker
===================

We recommend running crossbar within a Docker container. We build the
``simonsobs/ocs-crossbar`` container from the official `crossbar.io Docker
image`_, specifically the cpy3 version. Bundled within the container is a
simple OCS configuration that should work with the configuration
recommendations in this documentation.

If changes need to be made, then you will need to generate your own
configuration file as described above. To use a modified configuration in the
container you can either:

- Edit the default configuration file and rebuild the Docker image
- Mount the new configuration file over ``/ocs/.crossbar/config.json`` with the
  proper permissions

.. _`crossbar.io Docker image`: https://hub.docker.com/r/crossbario/crossbar

Rebuilding the Docker Image
---------------------------
To rebuild the Docker image after modifying ``ocs/docker/config.json`` run::

    $ docker build -t ocs-crossbar .

You should then update your configuration to use the new, local,
``ocs-crossbar`` image.

Bind Mounting the Configuration
-------------------------------
To instead mount the new configuration into the pre-built image, first chown
your file to be owned by user and group 242 (the default crossbar UID/GID),
then mount it appropriately in your docker-compsose file. Here we assume you
put the configuration in the direcitory ``./dot_crossbar/``::

    $ chown -R 242:242 dot_crossbar/

Your docker-compose service should then be configured like::

    crossbar:
    image: simonsobs/ocs-crossbar
    ports:
      - "8001:8001" # expose for OCS
    volumes:
      - ./dot_crossbar:/ocs/.crossbar
    environment:
         - PYTHONUNBUFFERED=1
