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
the ``FakeDataAgent`` class:

::

    def __init__(self, agent,
                 num_channels=2,
                 sample_rate=10.,
                 frame_length=60):
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()
        self.job = None
        self.channel_names = ['channel_%02i' % i for i in range(num_channels)]
        self.sample_rate = max(1e-6, sample_rate) # #nozeros

        # Register feed
        agg_params = {
            'frame_length': frame_length
        }
        print('registering')
        self.agent.register_feed('false_temperatures',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=0.)

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
to be included in the OCS-connected Agent directly. A good example of this is
in the `HKAggregatorAgent
<https://github.com/simonsobs/ocs/blob/develop/ocs/agent/aggregator.py>`.

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
                print("Agent initialized")
        # This part is for the record and to allow future calls to proceed, so does not require the lock
        self.initialized = True
        return True, 'Agent initialized.'


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

A simple example of this process can be found in the FakeDataAgent:

::

  if __name__ == '__main__':
    # Start logging
    txaio.start_logging(level=environ.get("LOGLEVEL", "info"))

    # Create an argument parser
    parser = add_agent_args()

    # Tell OCS that the kind of arguments you're adding are for an agent
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument("--port", help="Port connect to device on")
    pgroup.add_argument("--mode", default="idle", choices=['idle', 'acq'])

    # Process arguments, choosing the class that matches 'FakeDataAgent'
    args = site_config.parse_args(agent_class='FakeDataAgent', parser=parser)

    # Configure auto-startup based on args.mode
    startup = False
    if args.mode == 'acq':
        startup=True

    # Create a session and a runner which communicate over WAMP
    agent, runner = ocs_agent.init_site_agent(args)

    # Pass the new agent session to the agent class
    fdata = FakeDataAgent(agent,
                          num_channels=args.num_channels,
                          sample_rate=args.sample_rate,
                          frame_length=args.frame_length)

    # Register a process (name, agent_start_function, agent_end_function)
    agent.register_process('acq', fdata.start_acq, fdata.stop_acq,
                           blocking=True, startup=startup)

    # Register some tasks (name, agent_function)
    agent.register_task('set_heartbeat', fdata.set_heartbeat_state)
    agent.register_task('delay_task', fdata.delay_task, blocking=False)

    # Run the agent
    runner.run(agent, auto_reconnect=True)

Here we also set the Agent's commandline arguments using the built in Python
module ``argparse``. For details on how to using ``argparse`` with OCS see
:ref:`parse_args`.

Example Agent
-------------
For clarity and completeness, the entire FakeDataAgent is included here as an
example of a simple Agent.

.. include:: ../../agents/fake_data/fake_data_agent.py
    :code: python

Configuration
-------------
Because the agent program needs to be implemented in OCS, writing the agent
file is not sufficient for running it. Before you can run your agent, you
need to add an Agent instance to your ``default.yaml`` or ``your_institution.yaml``
file. To do this, change directories to ``ocs-site-configs/your_institution``.
Within this directory, you should find a yaml file to establish your OCS
agents. Within this file, you should find (or create) a dictionary of hosts.
As an example, we use the registry and aggregator agents, which are
necessary for taking any data with OCS, as well as the FakeDataAgent.

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

            # FakeDataAgent
            {'agent-class': 'FakeDataAgent',
             'instance-id': 'fake-data1',
             'arguments': [['--mode', 'acq'],
                           ['--num-channels', '16'],
                           ['--sample-rate', '4']]},
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

.. include:: ../../agents/ocs_plugin_standard.py
    :code: python

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
of this file is as follows (using the as FakeDataAgent an example):

.. include:: ../../agents/fake_data/Dockerfile
    :code: Dockerfile

In this case, the ``WORKDIR``, ``COPY``, and ``ENTRYPOINT`` arguments are all set 
specifically to the correct in-container paths to the directories and files for 
the FakeDataAgent. The final ``CMD`` argument provides a default for the
Crossbar (WAMP) connection. 

To include your new Agent among the services provided by your OCS Docker
containers, navigate to the ``docker-compose.yml`` file in the same sub-directory
as your ``default.yaml`` or ``your_institution.yaml`` file. Within 
``docker-compose.yml``, you should find (or create) a list of services that the
docker will run. You can add your new agent following the example format:

::

  services:
    fake-data1:
      image: simonsobs/ocs-fake-data-agent
      hostname: ocs-docker
      environment:
        - LOGLEVEL=info
      volumes:
        - ${OCS_CONFIG_DIR}:/config:ro
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

        python3 agent_name.py --instance-id=fake-data1

Here ``--instance-id`` is the same as that given in your ocs-site-configs
``default.yaml`` file. The agent will then run until it is manually ended.

Once your Agent is added to your docker-compose file, you can start all of your 
containerized Agents together with the command

::

        docker-compose up -d

Depending on your host's permissions, this command may need to be run with 
``sudo``.

