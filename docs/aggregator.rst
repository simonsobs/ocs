.. highlight:: rst

.. _aggregator:

==============
Aggregator
==============

SO3G File Format and Usage
--------------------------------
To store data we use a modified version of the SPT3G file format
tailored specifically to SO, called SO3g.
Like SPT3G, an SO3G consists of a sequence of *Frame* objects each containing
its own data. Each frame is a free-form mapping from strings to data
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
| IrregBlockDouble (so3g)| A map of multiple named elements along   |
|                        | with a single vector of timestamps.      |
+------------------------+------------------------------------------+

If you have SPT3G and so3g installed, you can view a g3 file by calling
``spt3g-dump filename so3g`` from the command line, which will display the
contents of the file as a dict. For instance, calling::

    $ spt3g-dump 2019-02-18_T_23:04:15.g3 so3g
    Frame (Housekeeping) [
    "description" (spt3g.core.G3String) => "HK data"
    "hkagg_type" (spt3g.core.G3Int) => 0
    "session_id" (spt3g.core.G3Int) => 1
    "start_time" (spt3g.core.G3Double) => 1.55056e+09
    ]
    Frame (Housekeeping) [
    "hkagg_type" (spt3g.core.G3Int) => 1
    "providers" (spt3g.core.G3VectorFrameObject) => [0x7fb6f4480130]
    "session_id" (spt3g.core.G3Int) => 1
    "timestamp" (spt3g.core.G3Double) => 1.55056e+09
    ]
    Frame (Housekeeping) [
    "agent_address" (spt3g.core.G3String) => "observatory.thermo1"
    "blocks" (spt3g.core.G3VectorFrameObject) => [0x7fb6f68840e0]
    "hkagg_type" (spt3g.core.G3Int) => 2
    "prov_id" (spt3g.core.G3Int) => 0
    "session_id" (spt3g.core.G3Int) => 1
    "timestamp" (spt3g.core.G3Double) => 1.55056e+09
    ]
    Frame (Housekeeping) [
    "agent_address" (spt3g.core.G3String) => "observatory.thermo1"
    "blocks" (spt3g.core.G3VectorFrameObject) => [0x7fb6f683fa20]
    "hkagg_type" (spt3g.core.G3Int) => 2
    "prov_id" (spt3g.core.G3Int) => 0
    "session_id" (spt3g.core.G3Int) => 1
    "timestamp" (spt3g.core.G3Double) => 1.55056e+09
    ]
    Frame (Housekeeping) [
    "agent_address" (spt3g.core.G3String) => "observatory.thermo1"
    "blocks" (spt3g.core.G3VectorFrameObject) => [0x7fb6f68635f0]
    "hkagg_type" (spt3g.core.G3Int) => 2
    "prov_id" (spt3g.core.G3Int) => 0
    "session_id" (spt3g.core.G3Int) => 1
    "timestamp" (spt3g.core.G3Double) => 1.55056e+09
    ]

Each so3g file will start with a Session frame and a Status frame,
giving information on the current aggregator session and active providers
respectively. You can see that this aggregator session has a single provider
writing data, and the agent address is ``aggregator.thermo1``.

To read from a g3 file, you can call ``file = core.G3File(filename)``.
``file`` is now an iterator that can loop through the frames in the file.

Aggregator Agent
--------------------------------
The aggregator agent's purpose is to take data being published by a general
Agent, and to write it to a so3g file.

The aggregator agent takes three site-config arguments.
``--initial-state`` can be either ``record`` or ``idle``,
and determines whether or not the aggregator starts recording
as soon as it is initialized.
``--time-per-file`` specifies how long each file should be in seconds,
and ``--data-dir`` specifies the default data directory.
Both of these can also be manually specified in ``params`` when
the ``record`` process is started.
An example site-config entry is
::

    {'agent-class': 'AggregatorAgent',
       'instance-id': 'aggregator',
       'arguments': [['--initial-state', 'record'],
                     ['--time-per-file', '3600'],
                     ['--data-dir', '/data/hk']
       ]},


To make sure that a feed is picked up
by the aggregator, it must be registered with the option 'record=True'.
It also must be registered with the frame_length, which tells the aggregator
how long each frame should be in seconds.
An example can be seen in LS240_agent.py::

    agg_params = {
        'frame_length': 60
    }
    self.agent.register_feed('temperatures',
                             aggregate=True,
                             agg_params=agg_params,
                             buffer_time=1)

A block is a set of timestreams that all share timestamps. They are written
together to an so3g object called an  `IrregBlockDouble`. In the LS240 example,
the agent says it will only need to write one block, with block_name `temps`
and the block will have two timestreams called `chan_1` and `chan_2`.
Here you can also add an optional block prefix that will be written to the so3g
file.

When publishing data to this feed, the message must be structured as::

    message = {
        'block_name': 'temps'
        'timestamp': timestamp of data
        'data': {
                'chan_1': datapoint1
                'chan_2': datapoint2
            }
    }

The message must contain exactly one data-point for each field of the block.
Timestreams that are not simultaneously sampled will have to be stored in
separate blocks and published separately.

.. autoclass:: agents.aggregator.aggregator_agent.DataAggregator
    :members: initialize, start_aggregate, write_blocks_to_file, add_feed






