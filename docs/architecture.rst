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

Agent Feeds:
-------------------------------------

Feeds are a useful way of passing data between agents.
These use a publish-subscribe pattern, where anytime data is published to a
feed, all subscribers are notified and a callback function is called with the
data as a parameter.

An ``OCSAgent`` can register a feed by calling::

    agent.register_feed(feed_name, agg_params={})

``agg_params`` holds information that is used by the aggregator to generate
SPT3G frames. For now, the only param used is ``aggregate`` which tells the
aggregator whether it should suscribe to the feed and write the data to a
G3Timestream. Eventually, this will also be able to determine how long the
frames should be, and the structure of the G3Frame.

You can publish data to a feed by calling::

    agent.publish_to_feed(feed_name, message)

In order to be passed through WAMP, the message must be serializable to JSON.
To pass class instances it is useful to write an ``encode`` function which puts
the relevant variables into a dict.

To subscribe to a feed you can call::

    agent.subscribe_to_feed(agent_addr, feed_name, callback, force_subscribe = False)

You must pass the address of the agent that registered the feed, and the name of
the feed along with a callback function that is called whenever the feed is
published to. The callback is passed a single parameter ``(message, feed_data)``
which is a tuple containing both the published message and the encoded feed that
sent it. An example of subscribing to feeds can be seen in
``agents/aggregator/aggregator_agent.py``.

``subscribe_to_feed`` by default protects against an agent subscribing to the
same feed multiple times. This is in case you want to run a client script
multiple times without restarting the agent, which can call
``subscribe_to_feed`` multiple times for the same feed. If you purposefully want
to subscribe to a feed more than once, you can set ``force_subscribe=True``.




