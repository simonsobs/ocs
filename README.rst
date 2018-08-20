================================
OCS - Observatory Control System
================================

Overview
========

The goal of OCS is to make it easy to coordinate hardware operation
and i/o tasks in a distributed system such as an astronomical
observatory.  The focus is on ease of use rather than performance.  By
"ease of use" we mean that the learning curve should be shallow; it
should be easy for new users to add or modify components; and the
software should run in a variety of environments (telescope, lab,
laptop) without much trouble.  By "rather than performance" we mean
that the system is not intended for real-timey, high throughput, Rube
Goldberg style automation.

The OCS provides python (and javascript) functions and classes to
allow "Control Clients" to talk to "Agents".  An Agent is a software
program that knows how to do something interesting and useful, such as
acquire data from some device or perform cleanup operations on a
particular file system.  A Control Client could be a web page with
control buttons and log windows, or a script written by a user to
perform a series of unattended, interlocking data acquisition tasks.

Installing
----------
Clone this repository and install using pip::

  git clone https://github.com/simonsobs/ocs.git
  cd ocs/
  pip3 install -r requirements.txt --user .

The OCS documentation can be built using sphinx once you've performed the
installation::

  cd docs/
  make html

You can then open ``docs/_build/html/index.html`` in your preferred web
browser.


Quick Start Example
-------------------

Open three terminals in the ``example/`` directory. Run the following
commands, in order, one command per terminal::

  make run_crossbar
  make run_agent
  make run_client

The first command, ``make run_crossbar`` will start an instance of crossbar.
(Note: If another OCS user is already running this, it will fail for you, but
you can use their already running instance.) The second command, ``make
run_agent`` starts the example OCS agent. This demos an imaginary hardware
device that knows how to perform operations such as tuning the SQUIDs. It
registers such tasks/processes for use by the client. Finally, the third command, ``make
run_client``, runs the example OCS client. This makes use of the registered
tasks and processes to perform some useful string of operations.

These will each print out a lot of log messages. But as long as you get more
log messages than error text, you're in good shape.

Web control example
-------------------

If the machine where you ran the example also has a GUI, you can open
a web browser and navigate on your local filesystem to the file in the
repository called www/monitor.html.  This exposes control buttons and
status windows for the Operations of the Agent that you launched with
"make run_agent".


Details
=======

Base layer: WAMP and crossbar
-----------------------------

The software entities in the system are able to talk to each other
using the WAMP protocol.  Although WAMP permits clients to sign up for
arbitrary RPC and Pub/Sub events, the OCS imposes a very limited set
of allowed interactions between the devices on the system.  The OCS
requires a WAMP router, such as crossbar.io.

Agent Operations: Tasks and Processes
-------------------------------------

A program that performs useful, specialized jobs in the system
registers itself as an "Agent".  The Agent makes available, to outside
callers, a set of Operations.  An Operation is a job that a Control
Client can request to be run.  An Operation can be either a Task or a
Process; these are distinguished by whether they should normally stop
on their own or not:

Task
  An Operation that, once started, can be expected to terminate on
  its own, in a finite time.

Process
  An Operation that, once started, should continue indefinitely unless
  stopped explicitly by user request or due to an error condition.

The API for controlling Operations is slightly different for Task and
Process.  Methods supported by Task and Process:

start(params)
  Request that the Operation be started; a hash of parameters can be
  passed to the Operation on startup.

status()
  Obtain the current status of the Operation.

wait(timeout)
  Block until the Operation becomes idle or the specified timeout has
  elapsed.

Methods supported only by Task:

abort()
  Demand that the current Task be stopped, even in an incomplete state.

Methods supported only by Operation:

stop()
  Request that the current Process be stopped.


Setting up OCS
==============

crossbar.io installation and configuration
------------------------------------------

crossbar.io is a WAMP router.  The router runs on a single computer,
and accepts connections on a particular TCP port.  All WAMP clients
that want to talk to each other connect to that router (using the
hostname or IP address and the websocket port number).

Crossbar can be obtained from the Python package index.  That means
you can get it as easily as::

  sudo pip3 install crossbar

Alternately you can install into your per-user space with::

  pip3 install --user crossbar

Note that we've used ``pip3`` to force an association with python3.
``pip3`` may be the same as ``pip`` on your system.

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
--------------------

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
-----

A simple, blocking Control Client can be written in python using only
the ``wampy`` library.  To get wampy, run one of::

  sudo pip3 install wampy
  pip3 install --user wampy

Such a client uses the module ocs.client_wampy.
