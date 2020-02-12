.. _installation:

Installation
============

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

.. _Docker Compose: https://docs.docker.com/compose/install/
