.. highlight:: rst

Software Installation
=====================

This page provides brief instructions, or links to external resources where
appropriate, for installation of software related to the live monitor.

Installing Docker
-----------------

Docker is used to run many of the components in the live monitor. While the
system can be run without Docker, it is the recommended deployment option. To
install, please follow the `installation`_ documentation on the Docker website.

.. note::

    The docker daemon requires root privileges. We recommend you run using sudo.

.. warning::

    While it is possible to run docker commands from a user in the ``docker``
    group, users in this group are considered equiavlent to the ``root`` user.

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

Install OCS with the following::

    $ git clone https://github.com/simonsobs/ocs.git
    $ cd ocs/
    $ pip3 install -r requirements.txt
    $ python3 setup.py install

.. note::

    If you want to install locally, not globally, throw the `--user` flag
    on both the pip3 and setup.py commands.

.. warning::

    The master branch is not guaranteed to be stable, you might want
    to checkout a particular version tag before installation depending on which
    other software you are working with. See the latest `tags`_.

These directions are presented in the `OCS repo`_, which likely has the most up
to date version. If you need to update OCS, be sure to stash any changes you've
made before pulling updates from the repo.

.. _installation: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _OCS repo: https://github.com/simonsobs/ocs
.. _post installation: https://docs.docker.com/v17.09/engine/installation/linux/linux-postinstall/
.. _tags: https://github.com/simonsobs/ocs/tags
