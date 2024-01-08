Implement Logging
-----------------

Our Agent contains several native Python print statements. While these do end
up in the logs it is better to use the logging system within OCS. We do so by
adding a log attribute to the Agent class. Focusing on just the addition of
``self.log`` this looks like:

.. code-block:: python

    class BarebonesAgent:
        """Barebone Agent demonstrating writing an Agent from scratch.

        Attributes:
            log (txaio.tx.Logger): Logger object used to log events within the
                Agent.

        """

        def __init__(self, agent):
            self.agent = agent
            self.log = agent.log
            self._count = False

Within the ``if __name__ == '__main__':`` block we need to do some additional
configuration, including setting the log level via environment variable:

.. code-block:: python

    # For logging
    txaio.use_twisted()
    LOG = txaio.make_logger()

    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

Now, any ``print()`` statement can become a ``self.log.info()`` statement.
There are additional levels to logging, including "debug". For more info on
logging see :ref:`txaio_logging`.

Agent Code
``````````

Our Agent in full now looks like this:

.. code-block:: python

    import time
    import txaio

    from os import environ

    from ocs import ocs_agent, site_config


    class BarebonesAgent:
        """Barebone Agent demonstrating writing an Agent from scratch.

        This Agent is meant to be an example for Agent development, and provides a
        clean starting point when developing a new Agent.

        Parameters:
            agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.

        Attributes:
            agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.
            log (txaio.tx.Logger): Logger object used to log events within the
                Agent.
            lock (TimeoutLock): TimeoutLock object used to prevent simultaneous
                commands being sent to hardware.
            _count (bool): Internal tracking of whether the Agent should be
                counting or not. This is used to exit the Process loop by changing
                it to False via the count.stop() command. Your Agent won't use this
                exact attribute, but might have a similar one.

        """

        def __init__(self, agent):
            self.agent = agent
            self.log = agent.log
            self._count = False

        def count(self, session, params):
            """count(test_mode=False)

            **Process** - Count up from 0.

            The count will restart if the process is stopped and restarted.

            Notes:
                The most recent value is stored in the session data object in the
                format::

                    >>> response.session['data']
                    {"value": 0,
                     "timestamp":1600448753.9288929}

            """
            # Initialize the counter
            self._count=True
            counter = 0

            self.log.info("Starting the count!")

            # Main process loop
            while self.count:
                counter += 1
                self.log.debug(f"{counter}! Ah! Ah! Ah!")
                session.data = {"value": counter,
                                "timestamp": time.time()}
                time.sleep(1)

            return True, 'Acquisition exited cleanly.'

        def _stop_count(self, session, params):
            """Stop monitoring the turbo output."""
            if self.count:
                self.count = False
                return True, 'requested to stop taking data.'
            else:
                return False, 'count is not currently running'

        @ocs_agent.param('text', default='hello world', type=str)
        def print(self, session, params):
            """print(text='hello world')

            **Task** - Print some text passed to a Task.

            Args:
                text (str): Text to print out. Defaults to 'hello world'.

            Notes:
                The session data will be updated with the text::

                    >>> response.session['data']
                    {'text': 'hello world',
                     'last_updated': 1660249321.8729222}

            """
            # Log the text provided to the Agent logs
            self.log.info(f"{params['text']}")

            # Store the text provided in session.data
            session.data = {'text': params['text'],
                            'last_updated': time.time()}

            # bool, 'descriptive text message'
            # True if task succeeds, False if not
            return True, 'Printed text to logs'


    def main(args=None):
        # For logging
        txaio.use_twisted()
        LOG = txaio.make_logger()

        # Start logging
        txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

        args = site_config.parse_args(agent_class='BarebonesAgent', args=args)

        agent, runner = ocs_agent.init_site_agent(args)

        barebone = BarebonesAgent(agent)
        agent.register_process(
            'count',
            barebone.count,
            barebone._stop_count)
        agent.register_task('print', barebone.print)

        runner.run(agent, auto_reconnect=True)


    if __name__ == '__main__':
        main()

Running the Agent
`````````````````

If we run the Agent now we will notice that the ``self.log.debug`` statements
no longer print by default to the logs (they would if ``LOGLEVEL=debug``), but
``self.log.info`` statements are still printed.

Client commands:

.. code-block:: python

    >>> from ocs.ocs_client import OCSClient
    >>> client = OCSClient('barebones1')
    >>> client.count.start()
    OCSReply: ERROR : Operation "count" already in progress.
      count[session=0]; status=running for 6.5 s
      messages (2 of 2):
        1658884651.313 Status is now "starting".
        1658884651.314 Status is now "running".
      other keys in .session: op_code, data
    >>> client.count.status().session['data']
    {'value': 15, 'timestamp': 1658884665.329796}
    >>> client.count.stop()
    OCSReply: OK : Requested stop on process "count".
      count[session=0]; status=running for 18.9 s
      messages (2 of 2):
        1658884651.313 Status is now "starting".
        1658884651.314 Status is now "running".
      other keys in .session: op_code, data

Agent logs:

.. code-block::

    2022-07-27T01:17:31+0000 start called for count
    2022-07-27T01:17:31+0000 count:0 Status is now "starting".
    2022-07-27T01:17:31+0000 Starting the count!
    2022-07-27T01:17:31+0000 count:0 Status is now "running".
    2022-07-27T01:17:37+0000 start called for count
    2022-07-27T01:17:50+0000 count:0 Acquisition exited cleanly.
    2022-07-27T01:17:50+0000 count:0 Status is now "done".

Next, we will learn about operation locking, allowing only a single task or
process to run at once.
