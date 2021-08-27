.. _session_data:

session.data
============

Data Feeds make use of the crossbar Pub/Sub functionality to pass data around
the network, however, sometimes you might not want to receive all data, just
the most recent values. For this purpose there is the ``session.data`` attribute.
This is a per OCS operation location to store recent data of interest to OCS
Agent users.  The ``session`` argument passed to each Operation function is an
object of class :class:`ocs.ocs_agent.OpSession`.

Often this is used to store the most recent values that are queried by the
Agent, for example the temperature of thermometers on a Lakeshore device. This
information can then be retrieved by a running OCS client and used to inform
operation of the Client, for instance waiting until a certain temperature set
point in your cryostat before starting detector data acquisition.

Agent Access
------------

To understand how to add data to the ``session.data`` object let's look at the
Fake Data Agent as an example, specifically at its primary Process,
``start_acq``:

.. code-block:: python
   :linenos:

    def start_acq(self, session, params=None):
        """**Process:**  Acquire data and write to the feed.

        This Process has no useful parameters.

        The most recent fake values are stored in the session.data object in
        the format::

            {"fields":
                {"channel_00": 0.10250430068515494,
                 "channel_01": 0.08550903376216404,
                 "channel_02": 0.10481891991693446,
                 "channel_03": 0.1060597011760155,
                 "channel_04": 0.1019265554541543,
                 "channel_05": 0.09389479275963578,
                 "channel_06": 0.10071855402986646,
                 "channel_07": 0.09601271802732826,
                 "channel_08": 0.09760831143883832,
                 "channel_09": 0.11345360178932645,
                 "channel_10": 0.10047676575328081,
                 "channel_11": 0.09534462609141414,
                 "channel_12": 0.09654199950059912,
                 "channel_13": 0.11051763608358373,
                 "channel_14": 0.1062686192067794,
                 "channel_15": 0.10793263271024509},
             "last_updated":1600448753.9288929}

        """
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg 
        session.set_status('running')

        if params is None:
            params = {}

        T = [.100 for c in self.channel_names]
        block = ocs_feed.Block('temps', self.channel_names)

        next_timestamp = time.time()
        reporting_interval = 1.
        next_report = next_timestamp + reporting_interval

        self.log.info("Starting acquisition")

        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10

            now = time.time()
            delay_time = next_report - now 
            if delay_time > 0:
                time.sleep(min(delay_time, 1.))
                continue

            # Safety: if we ever get waaaay behind, reset.
            if delay_time / reporting_interval < -3: 
                self.log.info('Got way behind in reporting: %.1s seconds. '
                              'Dropping fake data.' % delay_time)
                next_timestamp = now 
                next_report = next_timestamp + reporting_interval
                continue

            # Pretend we got it exactly.
            n_data = int((next_report - next_timestamp) * self.sample_rate)

            # Set the next report time, before checking n_data.
            next_report += reporting_interval

            # This is to handle the (acceptable) case of sample_rate < 0.
            if (n_data <= 0): 
                time.sleep(.1)
                continue

            # New data bundle.
            t = next_timestamp + np.arange(n_data) / self.sample_rate
            block.timestamps = list(t)

            # Unnecessary realism: 1/f.
            T = [_t + np.random.uniform(-1, 1) * .003 for _t in T]
            for _t, _c in zip(T, self.channel_names):
                block.data[_c] = list(_t + np.random.uniform(
                    -1, 1, size=len(t)) * .002)

            # This will keep good fractional time.
            next_timestamp += n_data / self.sample_rate

            # self.log.info('Sending %i data on %i channels.' % (len(t), len(T)))
            session.app.publish_to_feed('false_temperatures', block.encoded())

            # Update session.data
            data_cache = {"fields": {}, "last_updated": None}
            for channel, samples in block.data.items():
                data_cache['fields'][channel] = samples[-1]
            data_cache['last_updated'] = block.timestamps[-1]
            session.data.update(data_cache)

        self.agent.feeds['false_temperatures'].flush_buffer()
        self.set_job_done()
        return True, 'Acquisition exited cleanly.'

There's a lot going on here, which mostly has to do with generating the random
data that the Agent produces for testing. The part relevant for our discussion
is lines 95-100::

    # Update session.data
    data_cache = {"fields": {}, "last_updated": None}
    for channel, samples in block.data.items():
        data_cache['fields'][channel] = samples[-1]
    data_cache['last_updated'] = block.timestamps[-1]
    session.data.update(data_cache)


This block formats the latest values for each "channel" into a dictionary and
stores it in ``session.data``.


The structure of the ``data`` entry is not strictly defined, but
please observe the following guidelines:

- Document your ``data`` structure in the Operation docstring.
- Provide a `timestamp` with the readings, or with each group of
  readings, so that the consumer can confirm they're recent.
- The session data is passed to clients with every API response, so
  avoid storing a lot of data in there (as a rule of thumb, try to
  keep it < 100 kB).
- Fight the urge to store timestreams (i.e. a history of recent
  readings) -- try to use data feeds for that.
- When data are so useful that they are used by other clients /
  control scripts to make decisions in automated contexts, then they
  should also be pushed out to a data feed, so that there is a full
  record of all variables that were affecting system behavior.


.. note::
    You should consider the desired structure carefully, as future changes the
    data structure may cause existing clients that make use of the ``session.data``
    object to break. Changes that do take place should be announced in the
    change logs of new OCS versions.

Client Access
-------------
Once your Agent is storing information in the ``session.data`` object you
likely want to access it via an OCS client. The ``session`` object is returned
by all :ref:`Operation Methods<op_replies>`, for instance the ``status`` method, as shown in this small example::

    from ocs.matched_client import MatchedClient
    
    therm_client = MatchedClient('fake-data1')
    therm_client.acq.start()
    
    response = therm_client.acq.status()
    
After running the client we can examine the data dict stored within the response::

    >>> print(response.session.get('data'))
    {'fields': {'channel_00': 0.11220355191080153, 'channel_01':
    0.0850365880364649, 'channel_02': 0.16598799420080332, 'channel_03':
    0.26583693634591293, 'channel_04': 0.24601374140729332, 'channel_05':
    0.17319844739787155, 'channel_06': 0.1289138204655707, 'channel_07':
    0.21682049008200877, 'channel_08': 0.15539914447393058, 'channel_09':
    0.18161931031171688, 'channel_10': 0.040315857256297216, 'channel_11':
    0.06916760928468035, 'channel_12': 0.11291917165165984, 'channel_13':
    0.0996764253503196, 'channel_14': 0.019171783828962213, 'channel_15':
    0.06879881165286862}, 'last_updated': 1600717477.2989068}
