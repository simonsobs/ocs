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

Agent Feeds
========================================
Feeds are a useful way of passing data between agents.
These use a publish-subscribe pattern, where anytime data is published to a
feed, all subscribers are notified and a callback function is called with the
data as a parameter.

To add structure to the default WAMP pub/sub architecture, we use a wrapper
that handles the publishing part, caching published messages, and passing
information about the feed itself with the published data.

Feed API
---------
.. autoclass:: ocs.ocs_feed.Feed
    :members:



Registering Feeds
------------------------

An ``OCSAgent`` can register a feed by calling::

    agent.register_feed(feed_name, **kwargs)

where ``**kwargs`` are the keyword arguments passed to the Feed's init method
specified in the above API. This feed will publish data to the unique WAMP
address ``agent_address.feeds.feed_name``. For instance, in the LS240_Agent,
readout data is published to a registered feed called *temperatures*.
In this case, if I run LS240_Agent with instance-id ``thermo1``,
the agent_address will be ``observatory.thermo1`` and the feed's address
will be ``observatory.thermo1.feeds.temperatures``.

The dictionary ``agg_params`` is passed to the aggregator, and tells the
aggregator if and how a feed should be aggregated.
For now, the only param used is ``"aggregate"`` which determines whether
the aggregator should subscribe to the feed and write its data to a G3Timestream.
This is set by default to be False. Eventually, ``agg_params`` will also be able
to determine how long each frame should be, and the structure of the G3Frame.

Publishing to a Feed
----------------------
You can publish data to a feed by calling::

    agent.publish_to_feed(feed_name, message)

This publishes the tuple ``(message, feed_data)``  to the feed's address.
``message`` is the message passed to the ``publish_to_feed`` function,
and ``feed_data`` is a dictionary representation of the feed itself.
This dictionary contains the following fields:


==================   =================================================
agent_address        Address of the agent the feed is registered to.
feed_name            Name of the feed
address              Full WAMP address of the feed
messages             Cache of previous messages
agg_params           Parameters passed to the Aggregator
buffered             Specifies if Feed data is buffered
buffer_time          Specifies how long feed data is buffered,
                     or how long it should be buffered by the aggregator
==================   =================================================



Subscribing to a Feed
---------------------

To subscribe to a feed you can call::

    agent.subscribe_to_feed(agent_addr, feed_name, callback, force_subscribe = False)

You must pass the address of the agent that registered the feed, and the name of
the feed along with a callback function that is called whenever the feed is
published to.

The callback is passed the tuple ``(message, feed_data)``
where ``message`` is the published data, and ``feed_data`` is a dictionary
with the fields seen above.
An example of how this is used is seen in the Aggregator agent::

    def add_feed(self, agent_address, feed_name):
        """
        Subscribes to aggregated feed

        Args:
            agent_address (string):
                agent address of the feed.

            feed_name (string):
                name of the feed.
        """

        def _data_handler(_data):
            """Callback whenever data is published to an aggregated feed"""
            data, feed = _data
            if self.aggregate:
                self.incoming_data[feed["address"]].append(data)

        feed_address = "{}.feeds.{}".format(agent_address, feed_name)
        if feed_address in self.incoming_data.keys():
            return

        self.agent.subscribe_to_feed(agent_address, feed_name, _data_handler)
        self.incoming_data[feed_address] = []
        self.log.info("Subscribed to feed {}".format(feed_address))

This function is called whenever the aggregator needs to subscribe to a new feed.
It subscribes to the agent's feed with the callback ``_data_handler``,
which appends the received data to that feed's timestream.

``subscribe_to_feed`` by default protects against an agent subscribing to the
same feed multiple times. This is in case you want to run a client script
multiple times without restarting the agent, which can call
``subscribe_to_feed`` multiple times for the same feed. If you purposefully want
to subscribe to a feed more than once, you can set ``force_subscribe=True``.




