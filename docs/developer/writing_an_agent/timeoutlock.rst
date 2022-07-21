Operation Locking
-----------------

Currently our Agent has one Task and one Process. OCS is capable of running the
Task while the Process runs, however, when interacting with hardware you often
want to ensure that only one command is being sent to the hardware at a time.
To make Tasks/Processes exclusively have control over communication with a
hardware device when called we need to add the TimeoutLock.

Adding the simple case of locking out all other Operations during a Task or
Process would look like this:

.. code-block:: python

    def count(self, session, params):
        with self.lock.acquire_timeout(job='count') as acquired:
            if not acquired:
                self.log.warn(f"Could not start Process because "
                              f"{self.lock.job} is already running")
                return False, "Could not acquire lock"

            session.set_status('running')

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

    @ocs_agent.param('text', default='hello world', type=str)
    def print(self, session, params):
        with self.lock.acquire_timeout(job='print') as acquired:
            if not acquired:
                self.log.warn(f"Could not start Task because"
                              f"{self.lock.job} is already running")
                return False, "Could not acquire lock"

            # Set operations status to 'running'
            session.set_status('running')

            # Log the text provided to the Agent logs
            self.log.info(f"{params['text']}")

            # Store the text provided in session.data
            session.data = {'text': params['text']}

        # bool, 'descriptive text message'
        # True if task succeeds, False if not
        return True, 'Printed text to logs'

In this basic form the TimeoutLock will lock out any other Operation during
execution. We can see this if we run the Agent, start the count Process, and
try to run the print Task:

.. code-block::

    2022-07-22T15:54:46-0400 startup-op: launching count
    2022-07-22T15:54:46-0400 start called for count
    2022-07-22T15:54:46-0400 count:0 Status is now "starting".
    2022-07-22T15:54:46-0400 count:0 Status is now "running".
    2022-07-22T15:54:46-0400 Starting the count!
    2022-07-22T15:54:48-0400 start called for print
    2022-07-22T15:54:48-0400 print:1 Status is now "starting".
    2022-07-22T15:54:53-0400 Could not start Task because count is already running
    2022-07-22T15:54:53-0400 print:1 Could not acquire lock
    2022-07-22T15:54:53-0400 print:1 Status is now "done".

This behavior is typically fine for Tasks, but means we need to stop a running
Process before starting a Task. To handle this case the TimeoutLock has the
ability to temporarily release and then reacquire the lock, allowing short
Tasks to run during a Process loop. We will implement this here, but for more
details see :ref:`release_and_reacquire`.

Agent Code
``````````

Our Agent in full now looks like this:

.. code-block:: python

    import time
    import txaio
    
    from os import environ
    
    from ocs import ocs_agent, site_config
    from ocs.ocs_twisted import TimeoutLock
    
    
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
            self.lock = TimeoutLock(default_timeout=5)
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
            with self.lock.acquire_timeout(timeout=0, job='count') as acquired:
                if not acquired:
                    print("Lock could not be acquired because it " +
                          f"is held by {self.lock.job}")
                    return False
    
                session.set_status('running')
    
                # Initialize last release time for lock
                last_release = time.time()
    
                # Initialize the counter
                self._count=True
                counter = 0
    
                self.log.info("Starting the count!")
    
                # Main process loop
                while self._count:
                    # About every second, release and acquire the lock
                    if time.time() - last_release > 1.:
                        last_release = time.time()
                        if not self.lock.release_and_acquire(timeout=10):
                            print(f"Could not re-acquire lock now held by {self.lock.job}.")
                            return False
    
                    # Perform the process actions
                    counter += 1
                    self.log.debug(f"{counter}! Ah! Ah! Ah!")
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
                    {'text': 'hello world'}
    
            """
            with self.lock.acquire_timeout(timeout=3.0, job='print') as acquired:
                if not acquired:
                    self.log.warn("Lock could not be acquired because it " +
                                  f"is held by {self.lock.job}")
                    return False
    
                # Set operations status to 'running'
                session.set_status('running')
    
                # Log the text provided to the Agent logs
                self.log.info(f"{params['text']}")
    
                # Store the text provided in session.data
                session.data = {'text': params['text']}
    
            # bool, 'descriptive text message'
            # True if task succeeds, False if not
            return True, 'Printed text to logs'
    
    
    if __name__ == '__main__':
        # For logging
        txaio.use_twisted()
        LOG = txaio.make_logger()
    
        # Start logging
        txaio.start_logging(level=environ.get("LOGLEVEL", "info"))
    
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

Now if we try to run the print Task while the count Process is running we see
that print runs:

.. code-block::

    2022-07-22T16:09:43-0400 start called for count
    2022-07-22T16:09:43-0400 count:0 Status is now "starting".
    2022-07-22T16:09:43-0400 count:0 Status is now "running".
    2022-07-22T16:09:43-0400 Starting the count!
    2022-07-22T16:09:46-0400 start called for print
    2022-07-22T16:09:46-0400 print:1 Status is now "starting".
    2022-07-22T16:09:46-0400 hello world
    2022-07-22T16:09:46-0400 print:1 Status is now "running".
    2022-07-22T16:09:46-0400 print:1 Printed text to logs
    2022-07-22T16:09:46-0400 print:1 Status is now "done".

Next, we will add an OCS Feed and publish the count to it, saving data to disk!
