.. highlight:: rst

Software Installation
=====================

Installing Docker
-----------------

Docker is used to run many of the components related to sisock, including the
crossbar server, so we'll start by installing it on the computer we're running
everything on. To install, please follow the `Docker installation`_
documentation on their website.

.. note::

    The docker daemon requires root privileges. To avoid this you can add your user
    to the ``docker`` group. This is explained in the `post installation`_ steps,
    also in the Docker docs. However, we recommend you run as root through a
    sudo user.

When complete, the docker daemon should be running, you can check this by
running ``systemctl status docker`` and looking for output similar to the
following::

    $ systemctl status docker
    ● docker.service - Docker Application Container Engine
       Loaded: loaded (/lib/systemd/system/docker.service; disabled; vendor preset: enabled)
       Active: active (running) since Tue 2018-10-30 10:57:48 EDT; 2 days ago
         Docs: https://docs.docker.com
     Main PID: 1472 (dockerd)

If you see it is not active, run ``systemctl start docker``. To ensure it runs
after a computer reboot you should also run ``systemctl enable docker``.

Installing Docker Compose
-------------------------

Docker Compose facilitates running multi-container applications, which we have.
This will allow us to pull and run all the containers we need in a single
command. To install see the `Docker Compose`_ documentation.

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
    $ pip3 install -r requirements.txt --user .

These directions are presented in the `OCS repo`_, which likely has the most up
to date version. If you need to update OCS, be sure to stash any changes you've
made before pulling updates from the repo.


.. _Docker installation: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _OCS repo: https://github.com/simonsobs/ocs
.. _post installation: https://docs.docker.com/v17.09/engine/installation/linux/linux-postinstall/
