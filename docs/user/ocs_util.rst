.. highlight:: bash

.. _ocs_util:

==========
OCS Util
==========

Overview
========

In many situations you might want to run OCS clients or view so3g data without 
having to install the software on your local system. The OCS Util docker is a 
general purpose utility docker which can be used to easily view data or run 
ocs clients through a jupyter notebook or a command line interface.

Setup
=====

The OCS Util docker can be setup by putting the following entry in your system's
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

Then on docker-compose up, the ocs-util docker will automatically start up a 
jupyter server on port 8880, with a password "password". To change the port,
you can change the ``JUPYTER_PORT`` environment variable, and change the 
``ports`` entry to expose your chosen port.

.. warning::

    It is highly recommended that you change ``JUPYTER_PW`` to something other than 
    "password", since access to this notebook will give anyone the opportunity to run 
    arbitrary code from the "ocs" user.

Usage
=====

To access the notebook, simply direct your browser to ``localhost:<port>``, where
``<port>`` is what is specified in ``JUPYTER_PORT``. It will request a password,
which is set to the value you put in ``JUPYTER_PW``.

To connect remotely, you may have to tunnel the ``JUPYTER_PORT`` through to your
local computer, with::

    $ ssh -L <port>:localhost:<port> <user>@<host>

again, replacing ``<port>``, ``<user>``, and ``<host>`` with relevant info.


You can execute commands in the ``ocs-util`` docker with the ``docker-exec`` command.
For instance, once ``so3g-dump`` exists, you can run it on a datafile with::

    $ docker exec ocs-util so3g-dump /path/to/datafile

