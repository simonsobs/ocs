.. highlight:: rst

Dependencies
============

This is everything you will need to run the live monitor.

Hardware Requirements
---------------------

You will need a Linux computer running Ubuntu 18.04. Other
Operating Systems can be used, but will not be supported.

.. note::

    We'll be using Docker for a portion of this. This will pull images that
    containerize our applications, most of which are based on a base Python image.
    This will take disk space in your root filesystem. If you partition for a small
    / you might run into space constraints. In this case you should get in touch
    with Brian for advice on how best to proceed.

Software Requirements
---------------------

We'll need several pieces of software. To start:
    * Docker_ - Containerization software used for running sisock.
    * `Docker Compose`_ - Docker tool for running multi-container applications.
    * spt3g_ - For writing data to disk in ``.3g`` format.

SO software:
    * OCS_ - Our Observatory Control System.
    * sisock_ - For the live monitor. This will run in a Docker container, so
                we won't actually be installing it on our host system directly.

Networking Requirements
-----------------------

This Linux machine will need to go on the same network as whatever hardware
you're controlling with OCS. Live monitoring remotely (i.e. not sitting
directly at the computer) is facilitated if your IT department allows it to
have a public IP address.

.. warning::
    If you do have a public IP and traffic is allowed to
    all ports, you are strongly recommended to enable a firewall as described in
    :ref:`firewall`. Care should also be taken when exposing ports in Docker to
    expose only to your localhost (i.e. 127.0.0.1), this is the default in all
    templates provided by the DAQ group.

.. note::
    If you do not have a public IP, but do have access to a gateway to
    your private network, then port forwarding can be used to view the live monitor
    remotely, as described in :ref:`port_forwarding`.

.. _Docker: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _spt3g : https://github.com/CMB-S4/spt3g_software
.. _OCS: https://github.com/simonsobs/ocs
.. _sisock: https://github.com/simonsobs/sisock
