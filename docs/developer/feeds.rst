.. highlight:: rst

.. _feeds:

Data Feeds
==========
WAMP applications pass data between components via a publish/subscribe interface.
A component can publish data to a unique address, and then any other component
can register a callback to said address.
Any time data is published, the all subscribed components will receive that
data with the registered callback function.

The OCS Feed is a layer on top of this basic pub/sub functionality that agents
can use to pass data to other OCS agents or clients.
The OCS agent contains several methods which make it easy to register new feeds,
publish data to registered feeds, and subscribing to other agent's feeds.
The feed system adds some structure to the base pub/sub layer by adding
features such as data-caching, data and feed-name verification, and
aggregation behavior customization.


Registering Feeds
------------------------

An ``OCSAgent`` can register a basic feed by calling::

    agent.register_feed(feed_name)

The ``register_feed`` function takes a few other key word arguments to customize
its behavior (See :ref:`Feed Api <ocs_feed_api>` for more details).
``buffer_time`` will set how long the feed should buffer messages before sending
over crossbar, and ``max_messages`` will set how many messages are cached.

Feed_name Rules
````````````````

Data on this feed will be published to the URI ``<agent_uri>.feeds.<feed_name>``
so feed names must follow standard
`URI formatting rules <https://crossbar.io/docs/URI-Format/>`_, meaning
the feed can only use lowercase letters, numbers, and underscores.
As the ``agent_uri`` will be unique for each agent, feed names are not required
to be globally unique.

For instance, the Lakeshore372 agent may register a feed called ``temperatures``.
A Lakeshore372 instance with instance-id ``LSASIM`` would then publish data to
the URI ``observatory.LSASIM.feeds.temperatures``.

Agg Params
```````````
If you'd like your feed to be recorded by the hk aggregator, you must register
with the keyword ``record=True``, and you can customize the hk aggregator
behavior with the ``agg_params`` option.
The following options can be specified here:

.. list-table:: Aggregator params
    :widths: 20 20

    * - frame_length
      - Aggregation time (seconds) before frame is written to disk

    * - fresh_time
      - Time (seconds) before feed is considered "stale", and is removed from
        the HK status frame

Publishing to a Feed
----------------------
You can publish data to a feed by calling::

    agent.publish_to_feed(feed_name, message)

For standard feeds, message can be any json-ifyable object (i.e. strings, ints,
floats, bools, or dicts containing these).
Callbacks will receive the tuple ``(message, feed_data)`` where ``feed_data``
is a dict encoding most OCS.Feed attributes.

Recorded Feed Message Format
````````````````````````````
Recorded feeds require data to have a specific structure so that the aggregator
can encode the data into G3 objects.
Each message published should contain a ``block`` of data, or a group of data
that is co-sampled. Messages should have this structure::

    message = {
        'block_name': <Key to identify group of co-sampled data>
        'timestamp': <ctime of data>
        'data': {
            'field_name_1': <datapoint1>,
            'field_name_2': <datapoint2>
        }
    }

or if data is buffered on the agent-side, multiple co-sampled data points can
be passed at once as::

    message = {
        'block_name': <Key to identify group of co-sampled data>
        'timestamps': [ctime1, ctime2, ... ]
        'data': {
            'field_name_1': [data1_1, data1_2, ...],
            'field_name_2': [data2_1, data2_2, ...]
        }
    }

Note the pluralized ``timestamps`` key.

Data with consistent ``block_names`` will be written to disk as a single
``G3TimesampleMap`` object, which stores co-sampled data as a map containing
multiple G3Vector objects along with a vector of timestamps.
In the example above, the keys of the ``G3TimesampleMap`` will be
``field_name_1`` and ``field_name_2``.
The ``block_name`` is only used internally and will not be written
to disk.

Each set of data that a feed publishes that is non-cosampled should be
published to a different ``block_name``.
For instance, for the L372 agent data coming from separate channels are not
co-sampled.
The LS372 temperatures should then look like::

    message = {
        'block_name': 'channel_01',
        'timestamp': <ctime>,
        'data': {
            'channel_01_T': <channel 1 temperature reading>,
            'channel_01_V': <channel 1 voltage reading>
         }
    }

The LS372 G3Frames will then contain a G3TimesampleMap for each channel,
containing the temperature and voltage readings along with their timestamps.

Field Name Requirements
''''''''''''''''''''''
Field names must:

- Contain only letters, numbers, and underscores.
- Begin with a letter or any number of underscores followed by a letter.
- Be no longer than 255 characters.

Attempting to publish an invalid field name should raise an error by the agent.
However, if invalid field names somehow make it to the aggregator, the
aggregator will attempt to correct them before writing to disk.

Subscribing to a Feed
---------------------

There are a few different ways for your agent to subscribe to an OCS Feed.
Once the twisted reactor has started, both the ``subscribe_to_feed`` and
``subscribe`` functions can be used.
The ``subscribe_to_feed`` method takes the ``agent_address``, ``feed_name``,
and the callback function. By default, this function protects an agent from
subscribing to a topic multiple times.
The ``subscribe`` function provides more direct access to the Crossbar
subscription method.
It takes in the full topic URI along with an optional dict ``options`` to
specify more detailed subscription options such as pattern matching behavior.
For instance, the following line will subscribe to all OCS feeds in the
``observatory`` namespace::

    agent.subscribe(callback, 'observatory..feeds.', options={'match': 'wildcard'})

Before the reactor has started, the ``subscribe_on_start`` function can be used
to queue up a subscribe call to run as soon as the reactor starts.

Examples
--------
Here is an example showing how the ``registry`` agent subscribes its
heartbeat registration callback::

    class RegistryAgent:
        def __init__(self, agent):
            self.agent = agent
            self.agent.subscribe_on_start(
                self._register_heartbeat, 'observatory..feeds.heartbeat',
                options={'match': 'wildcard'}
            )

        def _register_heartbeat(self, _data):
            msg, feed = _data
            self.registered_agents[feed['agent_address']].refresh()

