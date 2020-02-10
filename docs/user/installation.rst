.. _installation:

Installation
============

Dependencies
------------

The system is designed to be distributed across many computers, however it can
also all be run on a single computer. This modular architecture means the
software and hardware requirements are quite flexible. Below are the minimum
hardware and software requirements for getting the live monitor running on a
single computer.

Software Requirements
---------------------

Installation will be covered in the next section, but these are the recommended
software dependencies:

    * Docker_ - Containerization software used for deploying several SO written
      packages.
    * `Docker Compose`_ - CLI tool for running multi-container Docker
      applications.

Python Dependencies
```````````````````
All python dependencies for OCS are listed in the ``requirements.txt`` file. Some
of the dependencies are:

* `crossbar.io`_ - An implementation of a WAMP router.
* `Autobahn`_ - Provides open-source implementations of WAMP.
* `twisted`_ - Used with Autobahn for networking.
* `wampy`_ - A non-asynchronus WAMP library providing RPC and Pub/Sub for
  Python applications.

.. _crossbar.io: https://crossbar.io/
.. _Autobahn: https://crossbar.io/autobahn/
.. _twisted: https://twistedmatrix.com/trac/
.. _wampy: https://github.com/noisyboiler/wampy

All dependencies are automatically installed via the ``requirements.txt`` file.

Hardware Requirements
---------------------

You will need a Linux computer running Ubuntu 18.04. Other
Operating Systems can be used, but are not officially supported.

.. note::

    Docker stores its images in the root filesystem by default. If the computer
    you are using has a small ``/`` partition you might run into space
    constraints.

Networking Requirements
-----------------------

This Linux machine will need to go on the same network as whatever hardware
you are controlling with OCS. Live monitoring remotely (i.e. not sitting
directly at the computer) is facilitated by having a public IP address, and if
you are able to setup a secure webserver. Doing so, however, is beyond the
scope of this guide.

.. warning::
    You should not run your crossbar server on a public IP without a properly
    configured firewall. Single-node configurations can just expose ports only to
    localhost (127.0.0.1), however, beyond that it is recommended a separate
    firewall is placed between your machine and the Internet. Note Docker
    manuiplates iptables to open ports and so a software firewall is likely not
    enough.

.. note::
    If you do not have a public IP, but do have access to a gateway to
    your private network, then port forwarding can be used to view the live monitor
    remotely.

For examples of possible network configurations see the socs documentation -
`Network Configuration`_.

Installing Docker
-----------------

Docker is used to run many of the components in the live monitor. While the
system can be run without Docker, it is the recommended deployment option. To
install, please follow the `installation`_ documentation on the Docker website.

.. note::

    The docker daemon requires root privileges. We recommend you run using sudo.

.. warning::

    While it is possible to run docker commands from a user in the ``docker``
    group, users in this group are considered equivalent to the ``root`` user.

When complete, the docker daemon should be running, you can check this by
running ``sudo systemctl status docker`` and looking for output similar to the
following::

    $ sudo systemctl status docker
    ● docker.service - Docker Application Container Engine
       Loaded: loaded (/lib/systemd/system/docker.service; disabled; vendor preset: enabled)
       Active: active (running) since Tue 2018-10-30 10:57:48 EDT; 2 days ago
         Docs: https://docs.docker.com
     Main PID: 1472 (dockerd)

If you see it is not active, run ``sudo systemctl start docker``. To ensure it
runs after a computer reboot you should also run ``sudo systemctl enable
docker``.

Installing Docker Compose
-------------------------

Docker Compose facilitates running multi-container applications.  This will
allow us to pull and run all the containers we need in a single command. To
install see the `Docker Compose`_ documentation.

When complete you should be able to run::

    $ docker-compose --version
    docker-compose version 1.22.0, build 1719ceb

.. note::

    The version shown here might not reflect the latest version available.

Installing OCS
--------------

Many of the OCS components will run in Docker containers which already have OCS
installed, however to run an OCS client from our host we need to install OCS.
To install, clone the repository and use pip to install::

  git clone https://github.com/simonsobs/ocs.git
  cd ocs/
  pip3 install -r requirements.txt .

.. note::

    If you want to install locally, not globally, throw the `--user` flag
    on both the pip3 and setup.py commands.

.. _Network Configuration: https://socs.readthedocs.io/en/latest/network.html
.. _Docker: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/

