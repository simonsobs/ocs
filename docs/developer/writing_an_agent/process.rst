Adding a Process
----------------

So far we have an Agent with a single Task. Tasks are meant to be short
operations that end in finite time. Often we want to collect data from a
housekeeping device indefinitely, for that we use a Process. We will add a
Process to the Barebones Agent that simply counts up from zero. To do so we add
two more class methods:

.. code-block:: python

   def count(self, session, params):
        """count()

        **Process** - Count up from 0.

        The count will restart if the process is stopped and restarted.

        Notes:
            The most recent value is stored in the session data object in the
            format::

                >>> response.session['data']
                {"value": 0,
                 "timestamp": 1600448753.9288929}

        """
        session.set_status('running')

        # Initialize the counter
        self._count=True
        counter = 0

        print("Starting the count!")

        # Main process loop
        while self._count:
            counter += 1
            print(f"{counter}! Ah! Ah! Ah!")
            session.data = {"value": counter,
                            "timestamp": time.time()}
            time.sleep(1)

        return True, 'Acquisition exited cleanly.'

    def _stop_count(self, session, params):
        """Stop monitoring the turbo output."""
        if self._count:
            self._count = False
            return True, 'requested to stop taking data.'
        else:
            return False, 'count is not currently running'

Additionally, we have to register the Process, like we did with the Task:

.. code-block::

   agent.register_process(
        'count',
        barebone.count,
        barebone._stop_count)

The 'count' Process looks much like a Task, however it contains a while loop
(with ``self._count`` initialized to False in the class' ``__init__()`` method.)
The Process loop will continue to run until stopped via a ``.stop()`` call.

When registering the Process we must provide a name, the main method for
running the Process, as well as a stop method. Since the stop method is
separate, but to an OCS Client it is apart of the Process as a whole we mark
the stop method as private with a leading underscore, this prevents it from
showing the Agent API, which Client developers will use when writing control
programs that interact with the Agent.

Agent Code
``````````

Our Agent in full now looks like this:

.. code-block:: python

    import time
    
    from ocs import ocs_agent, site_config
    
    
    class BarebonesAgent:
        """Barebone Agent demonstrating writing an Agent from scratch.
    
        This Agent is meant to be an example for Agent development, and provides a
        clean starting point when developing a new Agent.
    
        Parameters:
            agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.
    
        Attributes:
            agent (OCSAgent): OCSAgent object from :func:`ocs.ocs_agent.init_site_agent`.
            _count (bool): Internal tracking of whether the Agent should be
                counting or not. This is used to exit the Process loop by changing
                it to False via the count.stop() command. Your Agent won't use this
                exact attribute, but might have a similar one.
    
        """
    
        def __init__(self, agent):
            self.agent = agent
            self._count = False
    
        def count(self, session, params):
            """count()
    
            **Process** - Count up from 0.
    
            The count will restart if the process is stopped and restarted.
    
            Notes:
                The most recent value is stored in the session data object in the
                format::
    
                    >>> response.session['data']
                    {"value": 0,
                     "timestamp": 1600448753.9288929}
    
            """
            session.set_status('running')
    
            # Initialize the counter
            self._count=True
            counter = 0
    
            print("Starting the count!")
    
            # Main process loop
            while self._count:
                counter += 1
                print(f"{counter}! Ah! Ah! Ah!")
                session.data = {"value": counter,
                                "timestamp": time.time()}
                time.sleep(1)
    
            return True, 'Acquisition exited cleanly.'
    
        def _stop_count(self, session, params):
            """Stop monitoring the turbo output."""
            if self._count:
                self._count = False
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
            # Set operations status to 'running'
            session.set_status('running')
    
            # Print the text provided to the Agent logs
            print(f"{params['text']}")
    
            # Store the text provided in session.data
            session.data = {'text': params['text'],
                            'last_updated': time.time()}
    
            # bool, 'descriptive text message'
            # True if task succeeds, False if not
            return True, 'Printed text to logs'
    
    
    if __name__ == '__main__':
        args = site_config.parse_args(agent_class='BarebonesAgent')
        agent, runner = ocs_agent.init_site_agent(args)
        barebone = BarebonesAgent(agent)
        agent.register_process(
            'count',
            barebone.count,
            barebone._stop_count)
        agent.register_task('print', barebone.print)
        runner.run(agent, auto_reconnect=True)

Running the Agent
`````````````````

Run the Agent like we did previously, then we can use a Client to start the
count Process:

.. code-block::

    >>> from ocs.ocs_client import OCSClient
    >>> client = OCSClient('barebones1')
    >>> client.count.start()
    OCSReply: OK : Started process "count".
      count[session=0]; status=starting for 0.008996 s
      messages (1 of 1):
        1658512144.473 Status is now "starting".
      other keys in .session: op_code, data
    >>> client.count.status()
    OCSReply: OK : Session active.
      count[session=0]; status=running for 7.5 s
      messages (2 of 2):
        1658512144.473 Status is now "starting".
        1658512144.476 Status is now "running".
      other keys in .session: op_code, data
    >>> client.count.status().session['data']
    {'value': 13, 'timestamp': 1658512156.49813}
    >>> client.count.stop()
    OCSReply: OK : Requested stop on process "count".
      count[session=0]; status=running for 22.4 s
      messages (2 of 2):
        1658512144.473 Status is now "starting".
        1658512144.476 Status is now "running".
      other keys in .session: op_code, data

In the Agent logs you should see (truncating several counts):

.. code-block::

    2022-07-22T13:49:04-0400 start called for count
    2022-07-22T13:49:04-0400 count:0 Status is now "starting".
    2022-07-22T13:49:04-0400 count:0 Status is now "running".
    2022-07-22T13:49:04-0400 Starting the count!
    2022-07-22T13:49:04-0400 1! Ah! Ah! Ah!
    2022-07-22T13:49:05-0400 2! Ah! Ah! Ah!
    2022-07-22T13:49:06-0400 3! Ah! Ah! Ah!
    2022-07-22T13:49:07-0400 4! Ah! Ah! Ah!
    2022-07-22T13:49:08-0400 5! Ah! Ah! Ah!
    2022-07-22T13:49:09-0400 6! Ah! Ah! Ah!
    2022-07-22T13:49:27-0400 count:0 Acquisition exited cleanly.
    2022-07-22T13:49:27-0400 count:0 Status is now "done".

Next, we will replace the print statements here with use of the OCS logger.
