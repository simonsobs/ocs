.. highlight:: bash

.. _ocs_util:

==========
ocs-util
==========

Overview
========

In many situations you might want to run OCS clients or view so3g data without 
having to install the software on your local system. The ocs-util container is a 
general purpose utility docker container which can be used to easily view data
or run ocs clients through a jupyter notebook or a command line interface.

Setup
=====

The ocs-util container can be setup by putting the following entry in your system's
``docker-compose.yml`` file::

  ocs-util:
    image: ocs-util:latest
    container_name: ocs-util
    environment: 
      JUPYTER_PORT: 8880
      JUPYTER_PW: password
    volumes:
      - ${OCS_CONFIG_DIR}:/config
      - /data/:/data/
    ports:
      - 8880:8880

Then on docker-compose up, the ocs-util container will automatically start up a 
Jupyter Lab server on port 8880, with a password "password". To change the port,
you can change the ``JUPYTER_PORT`` environment variable, and change the 
``ports`` entry to expose your chosen port.

.. warning::

    It is highly recommended that you change ``JUPYTER_PW`` to something other than 
    "password", since access to this notebook will give anyone the opportunity to run 
    arbitrary code from the "ocs" user.

.. note::

    The ``/data/`` directory bind mounted to the container needs proper
    permissions for the Jupyter Lab server to write files to disk. The server runs
    as the `ocs` user and by default writes to ``/data``. To ensure proper
    permissions you should for :ref:`create_ocs_user`.

Usage
=====

To access the notebook, simply direct your browser to ``localhost:<port>``, where
``<port>`` is what is specified in ``JUPYTER_PORT``. It will request a password,
which is set to the value you put in ``JUPYTER_PW``.

To connect remotely, you may have to tunnel the ``JUPYTER_PORT`` through to your
local computer, with::

    $ ssh -L <port>:localhost:<port> <user>@<host>

again, replacing ``<port>``, ``<user>``, and ``<host>`` with relevant info.

.. note::
  
  You can easily see which port of an existing ocs-util container is open with 
  the `docker ps` command. When the ocs-util docker is running, the output might 
  look something like this::

    CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                        NAMES
    c34c91d57f14        ocs-util:latest     "jupyter notebook /d…"   24 minutes ago      Up 24 minutes       0.0.0.0:8880->8880/tcp       ocs-util

  Under the ``PORTS`` column, the line ``0.0.0.0:8880->8880/tcp`` means that port 
  8880 has been exposed, and that is how you can reach the jupyter server.


One common way of utilizing ``ocs-util`` is by using the ``docker-exec`` command, 
which will run an executable within the docker-container. For example, to enter
a bash environment inside ``ocs-util`` you can run::

  $ docker exec -it ocs-util bash

The ``-it`` flag specifies that stdin should remain open, allowing you to interact
with the bash shell. You can also run other commands, such as ``so3g-dump``
(as soon as its developed), which will allow you to view so3g files in a human
readable format::

  $ docker exec ocs-util so3g-dump /data/path/to/file.g3


