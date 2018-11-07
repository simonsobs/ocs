.. highlight:: rst

.. _aggregator:

==============
Aggregator
==============

SPT3G File Format and Usage
--------------------------------
An SPT3G file consists of a sequence of *Frame* objects, each containing
a particular set of data. Each frame is a free-form mapping from strings to data
of a type derived from G3FrameObject, which behave similarly to a python
dictionary. Notably, SPT3G files cannot directly store python lists, tuples, or
numpy arrays, but must be wrapped in appropriateG3FrameObject container classes.
Reasons for this are specified in the G3 documentation.

Examples of useful G3FrameObjects:

+------------------------+------------------------------------------+
| G3VectorDouble         | A vector of doubles. It acts like a      |
|                        | numpy array of doubles.                  |
+------------------------+------------------------------------------+
| G3Timestream           |  Acts like a Vector double with attached |
|                        |  sample rate, start time, stop time and  |
|                        |  units.                                  |
+------------------------+------------------------------------------+
| G3TimestreamMap        | A map of strings to G3Timestreams.       |
+------------------------+------------------------------------------+

If you have SPT3G installed, you can view a g3 file by calling ``spt3g-dump``
from the command line, which will display the contents of the file as a dict.
For instance, calling::

    $ spt3g-dump 2018-10-14_T_19\:02\:40.g3

    Frame (Housekeeping) [
    "TODs" (spt3g.core.G3TimestreamMap) => Timestreams from 2 detectors
    "Timestamps" (spt3g.core.G3TimestreamMap) => Timestreams from 2 detectors
    "feed" (spt3g.core.G3String) => "observatory.thermo1.feeds.temperatures"
    ]

You can see that the g3 file has a single frame, containing two
G3TimestreamMap's called ``TODs`` and ``Timestamps``, and a string ``feed``
containing the aggregated feed name.
In this case, ``TODs`` and ``Timestamps`` each contain two timestreams for
thermometers *thermA* and *thermB* containing the temperature data and
timestamps respectively.

To read from a g3 file, you can call ``file = core.G3File(filename)``.
``file`` is now an iterator that can loop through the frames in the file,
and access the timestream data.

Aggregator Agent
--------------------------------
The aggregator agent's purpose is to take data being published by a general
Agent, and to write it to a SPT3G file. To make sure that a feed is picked up
by the aggregator, it must be registered with
``agg_params["aggregate"] = True``, for example::

    agent.register_feed('temperatures', agg_params={'aggregate': True})

The aggregator will automatically find and subscribe to the aggregated feeds
using the agent's data from the registry.

Currently, we require an aggregated feed to publish its data as a dictionary.
The aggregator saves the data such that each feed is saved to a separate G3Frame,
with G3TimestreamMaps called ``TODs`` and ``Timestamps``,
containing the published data and timestamps respectively.
The keys of the published dictionary are used as the keys of the two
G3TimestreamMaps.

For example, here is how data is published from the Lakeshore 240 agent::

    data = {}
    for i, channel in enumerate(self.module.channels):
        data[self.thermometers[i]] = (time.time(), channel.get_reading())

    session.app.publish_to_feed('temperatures', data)

The aggregator will then write a G3Timestream for each thermometer on the 240.


.. autoclass:: agents.aggregator.aggregator_agent.DataAggregator
    :members: initialize, start_aggregate, add_feed_task






