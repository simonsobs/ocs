.. _installation:

Installation
============

To install ocs simply clone the repository and use pip to install. We'll assume
you do not have administrative rights on the system you are installing on. If
you do, feel free to remove the ``--user`` flag::

  git clone https://github.com/simonsobs/ocs.git
  cd ocs/
  pip3 install -r requirements.txt --user .

Dependencies
------------
* `crossbar.io`_ is a WAMP router.
* `Autobahn`_ provides open-source implementations of WAMP.
* `twisted`_ is used with Autobahn for networking.
* `wampy`_ is a non-asynchronus WAMP library providing RPC and Pub/Sub for
  Python applications.

.. _crossbar.io: https://crossbar.io/
.. _Autobahn: https://crossbar.io/autobahn/
.. _twisted: https://twistedmatrix.com/trac/
.. _wampy: https://github.com/noisyboiler/wampy

All dependencies are automatically installed via the ``requirements.txt`` file.
Below are details on each individual dependency.


crossbar.io installation and configuration
``````````````````````````````````````````

crossbar.io is a WAMP router.  The router runs on a single computer,
and accepts connections on a particular TCP port.  All WAMP clients
that want to talk to each other connect to that router (using the
hostname or IP address and the websocket port number).

Crossbar can be obtained from the Python package index.  That means
you can get it as easily as::

  sudo pip3 install crossbar

Alternately you can install into your per-user space with::

  pip3 install --user crossbar

crossbar does not launch automatically; instead you can launch a
session by running ``crossbar``.  The configuration file can be
specified at launch time; note that by default it will try to load
configuration from ``./.crossbar/config.json``.  In the ``example/``,
the Makefile command requests that crossbar load the configuration
from ``./dot_crossbar/``.

When a client connects, it also specifies the "realm" that it wants to
belong to.  Only clients registering on the same realm will be able to
"see" and communicate with each other.  This means that a single
router can be used for multiple, disjoint purposes.

Security (such as TLS on the socket, or password authentication) can
be added to the crossbar configuration file.  This is not implemented
in the current example, so it should only be run in trusted
environments.


twisted and autobahn
````````````````````

twisted and autobahn are for asynchronous i/o and WAMP, respectively.
These are required to run an OCS Agent.  They are also required to run
asynchronous Control Clients, such as example_ctrl.py.  However, one
can write Control Clients instead using the simpler, non-asynchronous
WAMP library called ``wampy``; see below.

To install autobahn and twisted, use ``pip``::

  sudo pip3 install autobahn twisted

or::
  
  pip3 install --user autobahn twisted


wampy
`````

A simple, blocking Control Client can be written in python using only
the ``wampy`` library.  To get wampy, run one of::

  sudo pip3 install wampy
  pip3 install --user wampy

Such a client uses the module ocs.client_wampy.
