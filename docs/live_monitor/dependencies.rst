.. highlight:: rst

Dependencies
============

The system is designed to be distributed across many computers, however it can
also all be run on a single computer. This modular architecture means the
software and hardware requirements are quite flexible. Below are the minimum
hardware and software requirements for getting the live monitor running on a
single computer.

Software Requirements
---------------------

Installation will be covered in the next section, but these are the required
software dependencies:

    * Docker_ - Containerization software used for deploying several SO written
      packages.
    * `Docker Compose`_ - CLI tool for running multi-container Docker
      applications.
    * OCS_ - The observatory control system, for running clients locally.

Hardware Requirements
---------------------

You will need a Linux computer running Ubuntu 18.04. Other
Operating Systems can be used, but will not be supported.

.. note::

    Docker stores its images in the root filesystem by default. If the computer
    you are using has a small ``/`` partition you might run into space
    constraints.  In this case you should get in touch with Brian for advice on
    how best to proceed.

Networking Requirements
-----------------------

This Linux machine will need to go on the same network as whatever hardware
you're controlling with OCS. Live monitoring remotely (i.e. not sitting
directly at the computer) is facilitated if your IT department allows it to
have a public IP address, and if you are able to setup a secure webserver.
Doing so, however, is beyond the scope of this guide.

.. warning::
    If you do have a public IP and traffic is allowed to
    all ports, you are strongly recommended to enable a firewall as described in
    :ref:`firewall`. Care should also be taken, when exposing ports in Docker, to
    expose your services, especially the crossbar server, to only your
    localhost (i.e. 127.0.0.1). This is the default in all templates provided
    by the SO DAQ group.

.. note::
    If you do not have a public IP, but do have access to a gateway to
    your private network, then port forwarding can be used to view the live monitor
    remotely, as described in :ref:`port_forwarding`.

.. _Docker: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _OCS: https://github.com/simonsobs/ocs
