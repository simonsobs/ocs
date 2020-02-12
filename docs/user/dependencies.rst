.. _dependencies:

Dependencies
============

The system is designed to be distributed across many computers, however it can
also all be run on a single computer. This modular architecture means the
software and hardware requirements are quite flexible. Below are the minimum
hardware and software requirements for getting the live monitor running on a
single computer.

Software Requirements
---------------------

Installation will be covered in the next section, but these are the recommended
software dependencies on host systems running OCS:

Python Dependencies
```````````````````
All python dependencies for OCS are listed in (and automatically installed via)
the ``requirements.txt`` file. Some of the dependencies are:

* `crossbar.io`_ - An implementation of a WAMP router.
* `Autobahn`_ - Provides open-source implementations of WAMP.
* `twisted`_ - Used with Autobahn for networking.
* `wampy`_ - A non-asynchronus WAMP library providing RPC and Pub/Sub for
  Python applications.

Other Dependencies
``````````````````

* Docker_ - Containerization software used for deploying several SO written
  packages.
* `Docker Compose`_ - CLI tool for running multi-container Docker
  applications.

Operating System
````````````````
Deploying in Docker makes OCS almost OS independent. If running components
directly on hosts we do recommend using Linux.

Linux
^^^^^
We recommend you run mostly in a Linux environment. Mostly we have deployed on
Ubuntu 18.04, and recommend you use that if possible. You are welcome to use
other Linux distributions, however support might be limited.

Windows
^^^^^^^
Some users have had success running OCS Agents in Docker on Windows 10, so that
is possible. This is often driven by the need to interface with some Windows
only software.

Mac
^^^
Some developers have also successfully run Dockerized OCS components on macOS.
However, no production systems are running macOS, so again, support might be
limited.

Hardware Requirements
---------------------

Hardware needs can be different depending on what OCS components you plan to
run on a machine. Generally you will need storage space for the Docker images.
Beyond that, even modest modern work stations can handle many components at
once.

.. note::

    Docker stores its images in the root filesystem by default. If the computer
    you are using has a small ``/`` partition you might run into space
    constraints.

If running OCS components on Windows 10 within Docker we recommend at least 8
GB of RAM, given that Windows needs to virtualize an environment to run Docker
in.

Networking Requirements
-----------------------

Simple OCS configurations can consist of a single machine. Beyond that, you
will need a local network, typically consisting of a private subnet defined by
a router. A network switch is often helpful in this case as well, depending on
the number of networked devices.

.. warning::
    You should not run your crossbar server on a public IP without a properly
    configured firewall. Single-node configurations can just expose ports only to
    localhost (127.0.0.1), however, beyond that it is recommended a separate
    firewall is placed between your machine and the Internet. Note Docker
    manuiplates iptables to open ports and so a software firewall is likely not
    enough.

    This firewall need is often satisified by those built into the router used
    to provide your OCS subnet.

Live monitoring remotely (i.e. not sitting directly at the computer) is
facilitated by having a public IP address, and if you are able to setup a
secure webserver. Doing so, however, is beyond the scope of this guide.

.. note::
    If you do not have a public IP, but do have access to a gateway to
    your private network, then port forwarding can be used to view the live monitor
    remotely.

For examples of possible network configurations see the socs documentation -
`Network Configuration`_.

.. _Network Configuration: https://socs.readthedocs.io/en/latest/user/network.html
.. _Docker: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _crossbar.io: https://crossbar.io/
.. _Autobahn: https://crossbar.io/autobahn/
.. _twisted: https://twistedmatrix.com/trac/
.. _wampy: https://github.com/noisyboiler/wampy
