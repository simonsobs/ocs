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
