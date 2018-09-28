.. highlight:: rst

.. _lakeshore372:

=============
Lakeshore 372
=============

The Lakeshore 372 (LS372) units are used for 100 mK and 1K thermometer readout.
Basic functionality to interface and control an LS372 is provided by the
``ocs.Lakeshore.Lakeshore372.py`` module.

LS372 OCS Quickstart
--------------------
To quickly get started acquiring data from a Lakeshore 372 with OCS perform the
following starting in the ocs directory (each in a separate terminal):

* Start the crossbar server::

    $ cd example/
    $ make run_crossbar

* Configure the aggregator data frame and file durations.

In ``agents/aggregator/aggregator_agent.py`` there is a method called
``start_aggregate``, this contains the following lines::

    time_per_frame = 60 * 10 # [s]
    time_per_file  = 60 * 60  # [s]

``time_per_frame`` indicates how often a Frame is flushed from memory to disk in
the 3g file. The current amount is every 10 minutes. ``time_per_file`` indicates
how often the file is closed out and a new one started. Currently this is every
hour. Since we do not currently have a live monitoring system in place this is
likely longer than you would like for the purposes of monitoring the data. You
will not be able to open the g3 file until the file is closed, so you likely
want to set both the frame and file duration to something short. The trade off
here is we will generate many files.

* Start the data aggregator agent::

    $ cd agents/aggregator/
    $ python3 aggregator_agent.py

* Configure the LS372 agent by putting the correct IP address in
  ``agents/thermometry/LS372_agent.py``::

    therm = LS372_Agent("LS372A", "10.10.10.2" , fake_data=False)

* Start the LS372 Agent::

    $ cd agents/thermometry/
    $ python3 LS372_agent.py

* Run the ``therm_and_agg_ctrl.py`` client. This will collect 30 seconds of data.
* You can change this in the client either by extending the ``sleep_time`` or by replacing the loop and data acquisiton and aggregator stop commands with a small sleep time, for instance, replacing::

    sleep_time = 10
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)


    print("Stopping Data Acquisition")
    yield get_data.stop()
    yield get_data.wait()

    print("Stopping Data Aggregator")
    yield aggregate.stop()
    yield aggregate.wait()

with::

    yield client_t.dsleep(.1)

This will cause the client to run the data acquisition and close. You will see
the data collected printed to the terminal ``LS372_agent.py`` is running. Data
is saved to ``ocs/agents/aggregator/data/``.

Sampling rate can be adjusted by changing the sleep time in ``LS372_agent.py``
on line 91::

    active_channel = self.module.get_active_channel()
    data[active_channel.name] = (time.time(), self.module.get_temp(unit='S', chan=active_channel.channel_num))
    time.sleep(.01)

Opening a 3g File
-----------------
This quick script will open the passed in 3g file::

    from spt3g import core
    import sys
    
    frames = [fr for fr in core.G3File(sys.argv[1])]

Save it (say as ``open.py``) and run with::

    python3 open.py <filename>

Data is then accessible in each frame, for instance::

    frames[0]['TODs'].keys()

This displays the channels recorded (should be only active ones) and then you
can access the data with ``frames[0]['TODs']['Channel 01']`` for instance.

Direct Communication
--------------------
Direct communication with the Lakeshore can be achieved without OCS, using the
``Lakeshore372.py`` module in ``ocs/ocs/Lakeshore/``. From that directory, you can run a script like::

    from Lakeshore372 import LS372

    ls = LS372('10.10.10.2')

You can use the API detailed on this page to then interact with the Lakeshore.
Each Channel is given a Channel object in ``ls.channels``. You can query the
resistance measured on the currently active channel with::

    ls.get_active_channel().get_resistance_reading()

That should get you started with direct communication. The API is fairly full
featured. Development on the Heater class is currently underway and has a
development branch on GitHub.

API
---

For the API all methods should start with one of the following:

    * set - set a parameter of arbitary input (i.e. set_excitation)
    * get - get the status of a parameter (i.e. get_excitation)
    * enable - enable a boolean parameter (i.e. enable_autoscan)
    * disable - disbale a boolean parameter (i.e. disable_channel)

.. automodule:: ocs.Lakeshore.Lakeshore372
    :members:
