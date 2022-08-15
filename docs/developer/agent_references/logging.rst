.. _txaio_logging:

Logging
-------

Log messages are critical to understanding what an Agent is doing at any given
moment. OCS uses the txaio_ package's log handler. All Agents have a
``self.log`` txaio logger object, which can be used within the Agent to log at
the various log levels (trace, debug, info, warn, error, critical). Agents will
automatically log things such as the starting and stopping of tasks and
processes.

A majority of OCS Agents will be deployed within Docker containers, and while
print statements would suffice, using a log handler provides a more detailed
way to track the logs. Within an ``ocs.agent`` object the ``self.log`` logger
should be used.

In the event you need to log other events outside the core Agent you will need
to add a logger. To add the txaio logger to your Agent file you will first need
to import txaio and intialize it. This can be done with::

    import txaio
    txaio.use_twisted()

If supporting classes are required, they should create their own loggers like::

    class SupportingClass():
        def __init__(self):
            self.log = txaio.make_logger()

        def useful_method(self, useful_argument):
            self.log.info('Log something useful.')

If you have supporting methods outside of the Agent and any supporting classes,
you should create a module wide logger with::

    LOG = txaio.make_logger()

Throughout the module you can then use::

    LOG.debug('a debug message')
    LOG.info('an info message')
    LOG.warn('a warning message')
    LOG.error('an error message')
    LOG.critical('a critical message')

The default log level is 'info'. To make use of log level selection, say to
print debug messages, we need to add a way to set the log level. For Docker
containers a convenient way of doing this is with Environment Variables. To add
this to your Agent use::

    if __name__ == '__main__':
        # Start logging
        txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

Then, in your docker-compose configuration file you can set the log level by
adding the environment block to your Agent's configuration::

    environment:
      - "LOGLEVEL=debug"

When you are done debugging, you can remove the block, or switch the level to
the default 'info'.

.. _txaio: https://txaio.readthedocs.io/en/latest/programming-guide.html#logging
