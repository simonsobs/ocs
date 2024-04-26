.. _ocs_install:

Installation
============

Installing Docker
-----------------

Docker is used to run many of the components in the live monitor. While the
system can be run without Docker, it is the recommended deployment option. To
install, please follow the `installation
<https://docs.docker.com/engine/install/ubuntu/>`_ documentation on the Docker
website.

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

    $ docker compose version
    Docker Compose version v2.25.0

.. note::

    The version shown here might not reflect the latest version available.

Installing OCS
--------------

Many of the OCS components will run in Docker containers which already have OCS
installed, however to run an OCS client from our host we need to install OCS.
To install, clone the repository and use pip to install::

  git clone https://github.com/simonsobs/ocs.git
  cd ocs/
  pip install -r requirements.txt .

.. note::

    If you want to install locally, not globally, throw the `--user` flag
    when installing with pip.

.. _Docker Compose: https://docs.docker.com/compose/install/

.. _create_ocs_user:

Creating the OCS User
`````````````````````
If you plan to run OCS within Docker (the recommended configuration) then you
should create the `ocs` user on your host system as well. This is the user
that is used within the Docker containers, and creating it on the host will
allow Agents that write to disk to write to bind mounted volumes within the
container.

The OCS user, `ocs`, has a UID of 9000, and a matching group, also called
`ocs`, with a GID of 9000. To create the group and user run::

    $ sudo groupadd -g 9000 ocs
    $ sudo useradd -u 9000 -g 9000 ocs

Next we need to create the data directory which the aggregator will write files
to. This can be any directory, for example, ``/data``, which we will use
throughout this documentation::

    $ sudo mkdir /data
    $ sudo chown 9000:9000 /data

Finally, we should add the current user account to the `ocs` group, replace
`user` with your current user::

    $ sudo usermod -a -G ocs user

These steps must only be performed once.
