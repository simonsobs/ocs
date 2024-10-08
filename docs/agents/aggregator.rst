.. highlight:: rst

.. _aggregator:

================
Aggregator Agent
================

The Aggregator Agent, also referred to as the Housekeeping Aggregator (or
HKAggregator), is the OCS Agent responsible for recording all data published to
the OCS Network's :ref:`feeds`. The Aggregator collects this data and writes it
to disk in the `.g3` file format.

.. warning::
    Be sure to follow the instructions for :ref:`create_ocs_user` during
    installation to ensure proper permissions for the Aggregator Agent to write
    data to disk.

.. argparse::
   :module: ocs.agents.aggregator.agent
   :func: make_parser
   :prog: agent.py

Dependencies
------------
The Aggregator Agent depends on both the `spt3g_software`_ and `so3g`_
packages.

Configuration File Examples
---------------------------

Below are configuration examples for the ocs config file and for running the
Agent in a docker container.

OCS Site Config
```````````````

The aggregator agent takes three site-config arguments.
``--initial-state`` can be either ``record`` or ``idle``,
and determines whether or not the aggregator starts recording
as soon as it is initialized.
``--time-per-file`` specifies how long each file should be in seconds,
and ``--data-dir`` specifies the default data directory.
Both of these can also be manually specified in ``params`` when
the ``record`` process is started.
An example site-config entry is::

    {'agent-class': 'AggregatorAgent',
       'instance-id': 'aggregator',
       'arguments': ['--initial-state', 'record',
                     '--time-per-file', '3600',
                     '--data-dir', '/data/hk']},

.. note::
    ``/data/hk`` is used to avoid conflict with other collections of data. In
    general, it is recommended to use ``/data/timestreams`` to store detector
    timestreams, and ``/data/pysmurf`` to store archived pysmurf files.


Docker Compose
``````````````

The docker image for the aggregator agent is simonsobs/ocs-aggregator-agent
Here is an example configuration::

    ocs-aggregator:
        image: simonsobs/ocs:latest
        container_name: ocs-aggregator
        hostname: ocs-docker
        user: "9000"
        environment:
          - LOGLEVEL=info
          - INSTANCE_ID=aggregator
        volumes:
          - ${OCS_CONFIG_DIR}:/config
          - /path/to/host/data:/data


Description
-----------
The job of the HK aggregator is to take data published by "Providers" and write
it to disk.
The aggregator considers each OCS Feed with ``record=True`` to be a separate
provider, and so any data written by a single OCS Feed will be grouped together
into G3Frames.
See :ref:`the OCS Feed page <recorded_feed_registration>` for info on how
to register a feed so that it will be recorded by the aggregator.

Unregistered providers will automatically be added when they send data,
and stale providers will be removed if no data is received in a specified
time period.

To do this, the aggregator monitors all feeds in the namespace defined
by the `{address_root}` prefix to find
feeds that should be recorded.  If the aggregator receives data from a feed
registered with ``record=True``, it will automatically add that feed as a
Provider, and will start putting incoming data into frames every ``frame_length``
seconds, where ``frame_length`` is set by the Feed on registration.
Providers will be automatically marked as stale and unregistered if it goes
``fresh_time`` seconds without receiving any data from the feed, where
``fresh_time`` is again set by the feed on registration.

The Aggregator Agent has a single main process ``record`` in which the
aggregator will continuously loop and write any queued up data to a G3Frame and
to disk.
The ``record`` task's session data object contains information such as the
path of the current G3 file, and the status of active and stale providers.

File Format and Usage
``````````````````````
Data is stored using the `spt3g_software`_ and `so3g`_ packages.  `so3g`_
provides the schema that operates on standard `G3 Frames`_. Each file consists
of a sequence of *Frame* objects each containing its own data. Each frame is a
free-form mapping from strings to data
of a type derived from G3FrameObject, which behave similarly to a python
dictionary. Notably, SPT3G files cannot directly store python lists, tuples, or
numpy arrays, but must be wrapped in appropriate G3FrameObject container classes.

Examples of useful G3FrameObjects:

.. list-table:: G3Objects
    :widths: 20 20

    * - G3VectorDouble
      - A vector of doubles. It acts like a numpy array of doubles
    * - G3Timestream
      - Acts like a Vector double with attached sample rate, start time, stop
        time, and units
    * - G3TimestreamMap
      - A map of strings to G3Timestreams.
    * - G3TimesampleMap
      - A map of vectors containing co-sampled data, packaged with a vector
        of timestamps.

The `so3g`_ package provides functions for loading data from disk. See
the `so3g Documentation <https://so3g.readthedocs.io/en/latest/hk.html>`_ for
details. If you simply need a quick look at the contents of a file you can use
the spt3g utility ``spt3g-dump``. For instance::

    $ spt3g-dump 1589310638.g3
    Frame (Housekeeping) [
    "description" (spt3g.core.G3String) => "HK data"
    "hkagg_type" (spt3g.core.G3Int) => 0
    "hkagg_version" (spt3g.core.G3Int) => 1
    "session_id" (spt3g.core.G3Int) => 426626618778213812
    "start_time" (spt3g.core.G3Double) => 1.58931e+09
    ]
    Frame (Housekeeping) [
    "hkagg_type" (spt3g.core.G3Int) => 1
    "hkagg_version" (spt3g.core.G3Int) => 1
    "providers" (spt3g.core.G3VectorFrameObject) => [0x7fdfe6cb4760]
    "session_id" (spt3g.core.G3Int) => 426626618778213812
    "timestamp" (spt3g.core.G3Double) => 1.58931e+09
    ]
    Frame (Housekeeping) [
    "address" (spt3g.core.G3String) => "observatory.faker.feeds.false_temperatures"
    "blocks" (spt3g.core.G3VectorFrameObject) => [0x7fdfe6d05760]
    "hkagg_type" (spt3g.core.G3Int) => 2
    "hkagg_version" (spt3g.core.G3Int) => 1
    "prov_id" (spt3g.core.G3Int) => 0
    "provider_session_id" (spt3g.core.G3String) => "1589308315.450184"
    "session_id" (spt3g.core.G3Int) => 426626618778213812
    "timestamp" (spt3g.core.G3Double) => 1.58931e+09
    ]

.. _spt3g_software: https://github.com/CMB-S4/spt3g_software
.. _so3g: https://github.com/simonsobs/so3g
.. _G3 Frames: https://cmb-s4.github.io/spt3g_software/frames.html

HK File Structure
`````````````````
The HK file is made up of three frame types: Session, Status, and Data,
labeled with an ``hkagg_type`` value of 0, 1, and 2 respectively.
Session frames occur once at the start of every file and contain information
about the current aggregation session, such as the ``session_id`` and
``start_time``.

Status frames contains a list of all active providers. One will always
follow the Session frame, and a new one will be written each time a provider
is added or removed from the list of active providers.

Data frames contain all data published by a single provider.
The data is stored under the key ``blocks`` as a list of G3TimesampleMaps, where
each timesample map corresponds to a group of co-sampled data, grouped by their
:ref:`block name <feed_message_format>`.
Each G3TimesampleMap contains a G3Vector for each ``field_name`` specified in the
data and a vector of timestamps.

Agent API
---------
.. autoclass:: ocs.agents.aggregator.agent.AggregatorAgent
    :members:

Supporting APIs
---------------
.. _agg_provider_api:

.. autoclass:: ocs.agents.aggregator.drivers.Provider
    :members:
    :noindex:

.. autoclass:: ocs.agents.aggregator.drivers.G3FileRotator
    :members:
    :noindex:

.. autoclass:: ocs.agents.aggregator.drivers.Aggregator
    :members:
    :noindex:
