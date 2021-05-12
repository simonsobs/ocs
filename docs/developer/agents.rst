Agents
======

In OCS, Agents are the software programs that contain the information you need
to do something useful. Agents can be used to communicate with hardware, or to
perform functions on preexisting data files. This guide will teach you how to
write a basic agent that can publish data to a feed.

Basics and Dependencies
-----------------------
An Agent is generally written as a Python class, and relies on modules
from OCS (including ``ocs_agent``, ``site_config``, ``client_t``, and
``ocs_twisted``). You must have OCS and all of its dependencies installed in
order to create and use an agent.

The OCS scripts ``ocs_agent``, ``site_config``, and ``client_t`` contain the
functionality required to register and run an agent using OCS and the crossbar
server. Functions from these scripts need to be called in order to run an 
Agent with OCS once your Agent script has been written.

First Steps
-----------
The purpose of an Agent is to provide any functionality that you may need in
order to do something, so it is generally useful to create a Python class for
the Agent. Your class should contain functions for any use to which you might
want to put your Agent; as such, the agent class can be as simple or complex
as you need it to be. Documentation for the parameters provided when initializing 
an Agent object should be wriiten in the docstring of the Agent class.

The ``__init__`` function of the class should contain the ability for your
agent to register functions in OCS (this will be addressed in more detail in 
the Registration and Running section of this guide). This can be added by 
including an ``agent`` variable in the function, which we will establish later 
with an ``ocs_agent`` function. A simple initialization function is given by 
the ``HWPSimulatorAgent`` class:

::

  def __init__(self, agent, port):
      self.active = True
      self.agent = agent
      self.log = agent.log
      self.lock = TimeoutLock()
      self.port = port
      self.take_data = False
      self.arduino = HWPSimulator(port = self.port)

      self.initialized = False

      agg_params = {'frame_length':60}
      self.agent.register_feed('amplitudes', record=True, agg_params=agg_params,
       buffer_time=1)


The ``agent`` variable provides both the log and the data feed, which are
important for storing and logging data through OCS. The ``__init__`` function
also includes the ``ocs_twisted`` class ``TimeoutLock``, which will be used in
every function of your class (see the next paragraph for more on this). The
function additionally sets a dictionary of ``agg_params`` (aggregator
parameters), which are used to inform the aggregator of the length of the G3
frames in which the data will be stored. The final line of the ``__init__``
function registers the feed with the aggregator, and requires four inputs:
the data feed being taken (here called ``'amplitudes'``), the ``record``
condition set to ``True`` in order to tell the aggregator to record data (or 
``False`` to not record data), the parameter dictionary, and a buffer time, 
usually set to 1.

In some Agents, it is convenient to create a separate class (or even an external
driver file) to write functions that the Agent class can call, but do not need
to be included in the OCS-connected Agent directly. In the case of the HWP 
Simulator agent, a separate HWPSimulator class is written to make a serial 
connection to the HWP simulator arduino and read data. Other Agents may require 
more complex helper classes and driver files (see ``LS240_Agent`` for an example).

Generally, a good first step in creating a function is to *lock* the function.
Locking checks that you are not running multiple functions simultaneously,
which helps to ensure that the Agent does not break if multiple functions are
mistakenly attempted at the same time. This is critical for Agents that interact 
with a hardware device to ensure that communication is properly controlled and 
that the device is not attempting to do multiple things at once.

In order to lock the function, we use the ``TimeoutLock`` class of ``ocs_twisted``. 
If a function cannot obtain the lock, the script should ensure that it does not 
start. The rest of the function should continue with this lock set. An example of 
the locking mechanism with an initialization function is written as follows:

::

        with self.acquire_timeout(timeout=0, job='init') as acquired:
                # Locking mechanism stops code from proceeding if no lock acquired
                if not acquired:
                        self.log.warn("Could not start init because {} is already running".format(self.lock.job))
                        return False, "Could not acquire lock."
                # Run the function you want to run
                try:
                        self.arduino.read()
                except ValueError:
                        pass
                print("HWP Simulator initialized")
        # This part is for the record and to allow future calls to proceed, so does not require the lock
        self.initialized = True
        return True, 'HWP Simulator initialized.'


Registration and Running
------------------------
After writing the necessary functions in the Agent class, we need to activate
the Agent through OCS. While the form of this activation will change slightly
depending on the Agent's purpose, there are a few steps that are necessary to
get our Agent up and running: adding arguments with ``site_config``, parsing
arguments, initializing the Agent with ``ocs_agent``, and registering tasks and
processes.

OCS divides the functions that Agents can run into two categories:

- *Tasks* are functions that have a built-in end. An example of this type of
  function would be one that sets the power on a heater.
- *Processes* are functions that run continuously unless they are told to stop
  by the user, or perhaps another function. An example of this type of function
  is one that acquires data from a piece of hardware.

A simple example of this process can be found in the HWP Simulator Agent:

::

  if __name__ == '__main__':

    # Create an argument parser
    parser = site_config.add_arguments()

    # Tell OCS that the kind of arguments you're adding are for an agent
    pgroup = parser.add_argument_group('Agent Options')

    # Tell OCS to read the arguments
    args = parser.parse_args()

    # Process arguments, choosing the class that matches 'HWPSimulatorAgent'
    site_config.reparse_args(args, 'HWPSimulatorAgent')

    # Create a session and a runner which communicate over WAMP
    agent, runner = ocs_agent.init_site_agent(args)

    # Pass the new agent session to the agent class
    arduino_agent = HWPSimulatorAgent(agent)

    # Register a task (name, agent_function)
    agent.register_task('init_arduino', arduino_agent.init_arduino)

    # Register a process (name, agent_start_function, agent_end_function)
    agent.register_process('acq', arduino_agent.start_acq, arduino_agent.stop_acq, startup=True)

    # Run the agent
    runner.run(agent, auto_reconnect=True)

If desired, ``pgroup`` may also have arguments (see ``LS240_agent`` for an
example).

Example Agent
-------------
For clarity and completeness, the entire HWP Simulator Agent is included here as an 
example of a simple Agent.

::

        from ocs import ocs_agent, site_config, client_t
        import time
        import threading
        import serial
        from ocs.ocs_twisted import TimeoutLock
        from autobahn.wamp.exception import ApplicationError

        # Helper  class to establish how to read from the Arduino
        class HWPSimulator:
                def __init__(self, port='/dev/ttyACM0', baud=9600, timeout=0.1):
                        self.com = serial.Serial(port=port, baudrate=baud, timeout=timeout)

                def read(self):
                        try:
                                data = bytes.decode(self.com.readline()[:-2])
                                num_data = float(data.split(' ')[1])
                                return num_data
                        except Exception as e:
                                print(e)

         # Agent class with functions for initialization and acquiring data
         class HWPSimulatorAgent:
                def __init__(self, agent, port='/dev/ttyACM0'):
                        self.active = True
                        self.agent = agent
                        self.log = agent.log
                        self.lock = TimeoutLock()
                        self.port = port
                        self.take_data = False
                        self.arduino = HWPSimulator(port=self.port)

                        self.initialized = False

                        agg_params = {'frame_length':60}
                        self.agent.register_feed('amplitudes', record=True, agg_params=agg_params, buffer_time=1}

                def init_arduino(self):
                        if self.initialized:
                                return True, "Already initialized."

                        with self.lock.acquire_timeout(timeout=0, job='init') as acquired:
                                if not acquired:
                                        self.log.warn("Could not start init because {} is already running".format(self.lock.job))
                                        return False, "Could not acquire lock."
                                try:
                                        self.arduino.read()
                                except ValueError:
                                        pass
                                print("HWP Simulator Arduino initialized.")
                        self.initialized = True
                        return True, "HWP Simulator Arduino initialized."

                def start_acq(self, session, params):
                        f_sample = params.get('sampling frequency', 2.5)
                        sleep_time = 1/f_sample - 0.1
                        if not self.initialized:
                                self.init_arduino()
                        with self.lock.acquire_timeout(timeout=0, job='acq') as acquired:
                                if not acquired:
                                        self.log.warn("Could not start acq because {} is already running".format(self.lock.job))
                                        return False, "Could not acquire lock."
                                session.set_status('running')
                                self.take_data = True
                                while self.take_data:
                                        data = {'timestamp':time.time(), 'block_name':'amps','data':{}}
                                        data['data']['amplitude'] = self.arduino.read()
                                        time.sleep(sleep_time)
                                        self.agent.publish_to_feed('amplitudes',data)
                                self.agent.feeds['amplitudes'].flush_buffer()
                        return True, 'Acquisition exited cleanly.'

                def stop_acq(self, session, params=None):
                        if self.take_data:
                                self.take_data = False
                                return True, 'requested to stop taking data.'
                        else:
                                return False, 'acq is not currently running.'

        if __name__ == '__main__':
                parser = site_config.add_arguments()

                pgroup = parser.add_argument_group('Agent Options')

                args = parser.parse_args()

                site_config.reparse_args(args, 'HWPSimulatorAgent')

                agent, runnr = ocs_agent.init_site_agent(args)

                arduino_agent = HWPSimulatorAgent(agent)

                agent.register_task('init_arduino', arduino_agent.init_arduino)
                agent.register_process('acq', arduino_agent.start_acq, arduino_agent.stop_acq, startup=True)

                runner.run(agent, auto_reconnect=True)


Configuration
-------------
Because the agent program needs to be implemented in OCS, writing the agent
file is not sufficient for running it. Before you can run your agent, you
need to add an Agent instance to your ``default.yaml`` or ``your_institution.yaml``
file. To do this, change directories to ``ocs-site-configs/your_institution``.
Within this directory, you should find a yaml file to establish your OCS
agents. Within this file, you should find (or create) a dictionary of hosts.
As an example, we use the registry and aggregator agents, which are
necessary for taking any data with OCS, as well as the HWP Simulator agent.

::

  hosts:

    grumpy: {

        'agent-instances': [
            # Core OCS Agents
            {'agent-class': 'RegistryAgent',
             'instance-id': 'registry',
             'arguments': []},
            {'agent-class': 'AggregatorAgent',
             'instance-id': 'aggregator',
             'arguments': [['--initial-state', 'record'],
                           ['--time-per-file', '3600'],
                           ['--data-dir', '/data/']]},

            # HWP Simulator Arduino
            {'agent-class': 'HWPSimulatorAgent',
             'instance-id': 'arduino',
             'arguments': []},
        ]
    }

When adding a new Agent, the ``'agent-class'`` entry should match the name of
your class in the Agent file. The ``'arguments'`` entry should match any
arguments that you added to ``pgroup`` at the end of your Agent file.

In this example, the ``'agent-instances'`` are found under a host called 
``grumpy``, which in this case is the name of the host computer. However, when 
writing an Agent that will be broadly useful, we may choose to Dockerize the 
Agent (and its dependencies). For more on this, see the Docker section of this 
documentation.


Agents additionally need to be registered in OCS central. In order to do this, 
it must be added to a list of Agents in ``socs/agents/ocs_plugin_so.py``. This 
script registers all of the agents you wish to run through the backend OCS site 
configuration. The list of Agents in this script is a list of tuples where the 
first element of the tuple is the name of the agent class, and the second element 
is the path to the Agent file (from the ``socs/agents`` directory). An example 
of this script is shown below:

::

        import ocs
        import os
        root =os.path.abspath(os.path.split(__file__)[0])

        for n,f in [
                ('Lakeshore372Agent', 'lakeshore372/LS372_agent.py'),
                ('Lakeshore240Agent', 'lakeshore240/LS240_agent.py'),
                ('BlueforsAgent', 'bluefors/bluefors_log_tracker.py'),
                ('HWPSimulatorAgent', 'hwp_sim/hwp_simulator_agent.py')
        ]:
            ocs.site_config.register_agent_class(n, os.path.join(root, f))


Docker
------
A Docker container creates a virtual environment in which you can package 
applications with their libraries and dependencies. OCS is recommended to be 
installed in a Docker container (for ease of installation). For Agents that are 
not meant solely to be used with one lab computer, it can be useful to add them 
to a Docker container as well. This requires creating a ``Dockerfile`` for your 
Agent and adding a new service to your OCS Docker Compose file,
``docker-compose.yml``. Adding your Agent in the ``docker-compose.yml`` file,
along with an appropriate data feed server service, will also allow you to view
your data feed when you run the Agent.

To create a ``Dockerfile``, change directories to the directory containing your 
Agent file. Within this directory, create a file called ``Dockerfile``. The format 
of this file is as follows (using the HWP Simulator as an example):

::

        # SOCS HWP Simulator Agent
        # socs Agent container for interacting with an HWP Simulator arduino

        # Use socs base image
        FROM socs:latest

        # Set the working directory to registry directory
        WORKDIR /app/agents/hwp_sim/

        # Copy this agent into the app/agents directory
        COPY . /app/agents/hwp_sim/

        # Run registry on container startup
        ENTRYPOINT ["python3", "-u", "hwp_simulator_agent.py"]

        CMD ["--site-hub=ws://crossbar:8001/ws", \
             "--site-http=http://crossbar:8001/call"]


In this case, the ``WORKDIR``, ``COPY``, and ``ENTRYPOINT`` arguments are all set 
specifically to the correct in-container paths to the directories and files for 
the HWP Simulator agent. The final ``CMD`` argument provides a default for the 
Crossbar (WAMP) connection. 

To include your new Agent among the services provided by your OCS Docker
containers, navigate to the ``docker-compose.yml`` file in the same sub-directory
as your ``default.yaml`` or ``your_institution.yaml`` file. Within 
``docker-compose.yml``, you should find (or create) a list of services that the
docker will run. You can add your new agent following the example format:

::

  services:
    hwp-simulator:
      image: grumpy.physics.yale.edu/ocs-hwpsimulator-agent:latest
      environment:
          TARGET: hwp-simulator
          NAME: 'hwp-simulator'
          DESCRIPTION: "hwp-simulator"
          FEED: "amplitudes"
      logging:
        options:
          max-size: "20m"
          max-file: "10"

The ``image`` line of this template corresponds to your Docker image (here, the 
``latest`` tag simply refers to the latest version of the image). Under 
``environment``, we establish entries that allow the data feed to subscribe to 
the data we are reading. The ``environment`` entries are:

- ``TARGET``: the same as the ``instance-id`` that you added in the previous
  file. This is used to identify the agent you wish to monitor.
- ``NAME``: the name that appears in a live feed field name.
- ``DESCRIPTION``: a short description of the feed you are subscribing to (can
  be a word or a short sentence).
- ``FEED``: the name of the agent feed you are reading. This must match the 
  feed name used in the ``self.agent.register_feed()`` entry in your agent class.

The ``logging`` entries establish parameters for keeping logs of your agent's 
activities. These options limit the maximum file size of the logs and
automatically rotates them. This should generally remain constant for all of
your agents.

Running the Agent
-----------------
If you do not initially include your Agent in your docker-compose file, you can 
run it from the command line with

::

        python3 agent_name.py --instance-id=hwp-simulator

Here ``--instance-id`` is the same as that given in your ocs-site-configs
``default.yaml`` file. The agent will then run until it is manually ended.

Once your Agent is added to your docker-compose file, you can start all of your 
containerized Agents together with the command

::

        docker-compose up -d

Depending on your host's permissions, this command may need to be run with 
``sudo``.

.. _timeout_lock:

TimeoutLock
------------

Overview
^^^^^^^^^

In OCS, operations are mainly asynchronous, however most agents have
restrictions on which operations are allowed to be run simultaneously.
For instance, when an Agent interfaces with a hardware device over serial
communication, two commands cannot be issued simultaneously.
In these cases, it may be required for agents to create a `lock` which restricts
what operations can run concurrently.
Requiring this lock to be acquired before any device communication is one
way to ensure that serial messages are not crossed, or avoid any other
dangerous asynchronous behavior.

The ocs :ref:`TimeoutLock <ocs_twisted_api>` is a lock that implements a few useful additions to the
standard ``threading.lock``. Mainly:

- It can be acquired by the ``acquire_timeout`` context
  manager, which will automatically release even if an exception is raised.
- A ``job`` string can be set on acquisition, describing the job obtaining
  the lock.
- The ``release_and_acquire`` function can be used to release the lock so that
  short operations can safely run during long-running processes.
- A ``timeout`` can be set to limit how long an operation will wait for the
  lock before failing.

Examples
^^^^^^^^^
acquire_timeout
```````````````
The following example shows how to acquire the TimeoutLock with the
``acquire_timeout`` context manager::

    lock = TimeoutLock()

    with lock.acquire_timeout(timeout=3.0, job='acq') as acquired:
        if not acquired:
            print(f"Lock could not be acquired because it is held by {lock.job}")
            return False
        # Any lock-requiring actions go here
        print("Lock acquired!")


Release and Reacquire
``````````````````````
Here is a slightly more complicated example that shows how an operation might
use the ``release_and_acquire`` function to allow other operations to interject
without completely giving up the lock.

This example shows a simple agent with two operations.
``start_acquisition`` starts a long-running process that can run in a separate
thread that takes the lock and acquires data until ``stop_acquisition`` is run.
``short_action`` is a task that requires the lock, and performs an action that
terminates quickly.
In this case, the acquisition process will release and acquire the lock about
every second, which allows the short action to be run safely without stopping
the acquisition process.
Because the short task acquires the lock with `timeout=3`, it will wait for the
lock for at least 3 seconds, which is long enough that we can be fairly certain
the process will drop the lock::

    class SimpleAgent():
        def __init__(self):
            self.lock = TimeoutLock()

        def short_action(self, session, params=None):
            with self.acquire_timeout(timeout=3, job='short_action') as acquired:
                if not acquired:
                    print(f"Lock could not be acquired because it is held by {self.lock.job}")
                    return False

                # Code that requires lock
                print("Running terminating operation")
                time.sleep(1)

        def start_acquisition(self, session, params=None):
            with self.lock.acquire_timeout(timeout=0, job='acq') as acquired:
                if not acquired:
                    print(f"Lock could not be acquired because it is held by {self.lock.job}")
                    return False

                # Any functionality that requires the lock can go within the
                # ``with`` statement
                last_release = time.time()
                self.run_acq = True
                while self.run_acq:
                    # About every second, release and acquire the lock
                    if time.time() - last_release > 1.:
                        last_release = time.time()
                        if not self.lock.release_and_acquire(timeout=10):
                            print(f"Could not re-acquire lock now held by {self.lock.job}.")
                            return False

                    print("Acquiring Data")
                    time.sleep(0.1)

        def stop_acquisition(self, session, params=None):
            self.run_acq = False

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
