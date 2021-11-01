.. highlight:: rst

.. _architecture:

Architecture of the OCS
=======================

Base layer: WAMP and crossbar
-----------------------------

The software entities in the system are able to talk to each other
using the WAMP protocol.  Although WAMP permits clients to sign up for
arbitrary RPC and Pub/Sub events, the OCS imposes a very limited set
of allowed interactions between the devices on the system.  The OCS
requires a WAMP router, such as crossbar.io.

.. _agent_ops:

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

Python Dependencies
-------------------
crossbar.io
```````````
crossbar.io is a WAMP router.  The router runs on a single computer,
and accepts connections on a particular TCP port.  All WAMP clients
that want to talk to each other connect to that router (using the
hostname or IP address and the websocket port number).

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
twisted and autobahn are for asynchronous I/O and WAMP, respectively.
These are required to run an OCS Agent. They are also required to run
asynchronous Control Clients, such as example_ctrl.py. However, simple clients
can be written in the usual Python synchronous framework, without any need for
twisted or autobahn.
