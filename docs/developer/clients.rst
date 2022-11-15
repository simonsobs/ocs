.. highlight:: python

.. _clients:

Clients and Control Programs
============================

The OCS Client ("Client") is used to command and control a corresponding OCS
Agent ("Agent"). Conceptually, this is the piece of OCS that connects to the
crossbar server and makes the "remote procedure call" to an Agent. Multiple
Clients can be used to orchestrate an observatory within a Control Program
("program" or "script").

While there are other options for how a Client could be implemented, the focus
of this documentation will be on using the OCSClient object within a script.
Other options are discussed below.

.. _ocs_client:

OCSClient
---------
The OCSClient (the object, not the concept of "Client") is the primary method
for interaction with an Agent. An OCSClient object provides the Agent's
Operation methods as attributes (replacing spaces and hyphens in Operation
names if they exist). The OCSClient requires the Agent's instance-id as an
argument. An OCSClient can be quickly setup using :ref:`client_cli`.

Basic Usage
```````````
To instantiate an OCSClient run (replacing
'agent-instance-id' with your Agent's unique instance-id):

.. code-block:: python

    from ocs.ocs_client import OCSClient
    client = OCSClient('agent-instance-id')

The returned object, ``client``, is populated with attributes for each Task and
Process (referred to generally "Operation") exposed by the OCS Agent with the
specified ``agent-instance-id``. Each of these attributes has a set of methods
associated with them for controlling the Operation. The methods for running an
Agent's Operations are described in :ref:`agent_ops`. They are "start",
"status", "wait", "stop" (Process only) and "abort" (Task only).

Once the Client is instantiated, Operations can be commanded, for example, to
start a Process called 'acq' (a common Process name for beginning data
acquisition)::

    >>> client.acq.start()
    OCSReply: OK : Started process "acq".
      acq[session=7]; status=starting for 0.007544 s
      messages (1 of 1):
        1635817216.260 Status is now "starting".
      other keys in .session: op_code, data

Once a Process is started, it will run until stopped. To stop the 'acq' Process
run::

    >>> client.acq.stop()
    OCSReply: OK : Requested stop on process "acq".
      acq[session=7]; status=running for 3.5 s
      messages (2 of 2):
        1635817216.260 Status is now "starting".
        1635817216.262 Status is now "running".
      other keys in .session: op_code, data

We can check that the Process has stopped by then calling "status"::

    >>> client.acq.status()
    OCSReply: OK : Session active.
      acq[session=7]; status=done without error 3.5 s ago, took 4.0 s
      messages (5 of 5):
        1635817216.260 Status is now "starting".
        1635817216.262 Status is now "running".
        1635817219.756 Status is now "stopping".
        1635817220.264 Acquisition exited cleanly.
        1635817220.265 Status is now "done".
      other keys in .session: op_code, data

When an Operation method is called in a Client the call returns immediately.
However, you might want to wait for a Task to complete before proceeding. This
can be accomplished with the "wait" method::

    >>> client.delay_task.start(delay=1)
    OCSReply: OK : Started task "delay_task".
      delay_task[session=6]; status=starting for 0.007555 s
      messages (1 of 1):
        1635791278.562 Status is now "starting".
      other keys in .session: op_code, data
    >>> client.delay_task.wait()
    OCSReply: OK : Operation "delay_task" is currently not running (SUCCEEDED).
      delay_task[session=6]; status=done without error 0.007504 s ago, took 1.0 s
      messages (4 of 4):
        1635791278.562 Status is now "starting".
        1635791278.563 Status is now "running".
        1635791279.566 Exited after 1.0 seconds
        1635791279.567 Status is now "done".
      other keys in .session: op_code, data

A shortcut for this "start" and then "wait" is to call the Task directly::

    >>> client.delay_task(delay=1)

This starts the Task and then immediately waits for it to complete (assuming
the task starts successfully), equivalent to::

    response = client.delay_task.start(delay=1)
    if response[0] == ocs.OK:
        client.delay_task.wait()

Direct calls to a Process behave a bit differently, acting as an alias to
"status", making these two calls identical::

    >>> client.acq.status()
    >>> client.acq()

The response given by any of these Operation method calls is an
:class:`ocs.ocs_client.OCSReply` object.  For more details see
:ref:`op_replies`.

Passing Arguments to an Operation
`````````````````````````````````

If an Operation has any arguments to provide at start, they can be passed as
you would typically pass keyword arguments in Python. For example, to pass a
delay of 1 second to the :ref:`fake_data_agent` Task "delay_task"::

    >>> client.delay_task.start(delay=1)
    OCSReply: OK : Started task "delay_task".
      delay_task[session=4]; status=starting for 0.008681 s
      messages (1 of 1):
        1635790951.261 Status is now "starting".
      other keys in .session: op_code, data

Arguments can also be passed to a direct call of the Task::

    >>> client.delay_task(delay=1)

You can of course use ``**`` to unpack a dict containing the required keyword
arguments. For example::

    >>> arguments = {'arg1': 1, 'arg2': 2, 'arg3': 3}
    >>> client.task(**arguments)

This is equivalent to::

    >>> client.task(arg1=1, arg2=2, arg3=3)

.. _op_replies:

Replies from Operation methods
``````````````````````````````

Responses obtained from OCSClient calls are lightly wrapped by
class :class:`ocs.ocs_client.OCSReply` so that ``__repr__``
produces a nicely formatted description of the result.  For example::

    >>> response = client.delay_task.status()
    >>> print(response)
    OCSReply: OK : Session active.
      delay_task[session=6]; status=done without error 76.4 mins ago, took 1.0 s
      messages (4 of 4):
        1635791278.562 Status is now "starting".
        1635791278.563 Status is now "running".
        1635791279.566 Exited after 1.0 seconds
        1635791279.567 Status is now "done".
      other keys in .session: op_code, data

OCSReply is a namedtuple. The elements of the tuple are:

  ``status``
    An integer value equal to ocs.OK, ocs.ERROR, or ocs.TIMEOUT (see
    :class:`ocs.base.ResponseCode`).

  ``msg``
    Short for "message", a string providing a brief description of the result
    (this is normally pretty boring for successful calls, but might contain a
    helpful tip in the case of errors.)

  ``session``
    The ``session`` portion of the reply is dictionary containing useful
    information, such as timestamps for the Operation's start and end, a
    success code, and a custom data structure populated by the Agent.

    The information can be accessed through the OCSReply, for example::

      >>> response = client.acq.status()
      >>> response.session['start_time']
      1585667844.423

    For more information on the contents of ``.session``, see the
    docstring for :func:`ocs.ocs_agent.OpSession.encoded` and the Data
    Access section on :ref:`session_data`.

Examples
````````

This section contains some examples for what you might want to accomplish with
a control program. Examples here do not show use of actual OCS Agents, but
should demonstrate proper use of the OCSClient API.

Check Whether a Task Completed Successfully or Not
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The OCSReply session dictionary can be used to check for successful completion
of a Task::

    from ocs.ocs_client import OCSClient

    client = OCSClient('agent-instance-id')
    response = client.random_task()

    # Will be True or False depending on successful completion
    if response.session['success']:
        print('Task completed successfully')
    else:
        print('Task did not complete successfully')

Check Latest Data in an Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If an Operation makes use of ``session.data``, a control program can check this
through the Client and react accordingly::

    from ocs.ocs_client import OCSClient

    client = OCSClient('agent-instance-id')
    response = client.random_task()

    print(response.session['data'])

.. note::
    The format of ``response.session['data']`` is left to the Agent author. For
    details on the format for a given Operation, see the Agent's reference page.

For more details about ``session.data`` see :ref:`session_data`.

Interacting with Multiple Agents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A control program can interact with multiple Agents by settings up multiple
OCSClients::

    from ocs.ocs_client import OCSClient

    client1 = OCSClient('agent-instance-id-1')
    client2 = OCSClient('agent-instance-id-2')

    # Start acquisition on client 1 and start a task on client 2
    client1.acq.start()
    client2.random_task()

A more useful example might be a program that interacts with a temperature
controller and detector readout::

    from ocs.ocs_client import OCSClient

    temperature_client = OCSClient('temperature-controller-agent')
    detector_client = OCSClient('detector-agent')

    temperatures = [100e-3, 110e-3, 120e-3, 130e-3, 140e-3, 150e-3, 160e-3]

    for t in temperatures:
        # Stop data acquisition if it is running
        temperature_client.acq.stop()

        # Set servo
        temperature_client.servo(temperature=t)

        # Start data acquisition
        temperature_client.acq.start()

        # Check temperature in session.data
        response = temperature_client.acq()

        current_temperature = response.session['data']['Channel 01']

        # insert check of temperature stability with repeated checks of
        # response.session['data'] here, proceeding once stable

        # Run detector measurement
        detector_client.run_measurement()

    # Reset servo to lowest temperature once done
    temperature_client.servo(temperature=temperatures[0])

Alternative Clients/Programs
----------------------------
``OCSClient`` is not the only form a "Client" could take.  Clients can be
written in any language supported by crossbar, however most commonly these will
be written in Python or JavaScript. In this section we cover some of these
alternative Client implementations.

ocs-web control panels
``````````````````````

A web-based graphical user interface, written in the Vue 3 framework,
is maintained here: https://github.com/simonsobs/ocs-web/ .
Specialized control panels can be written for each Agent to expose
some or all of an Agent's operations and session data.


Control Programs using Twisted
``````````````````````````````

.. note::

    Unless you are familiar with Twisted, and know you need an asynchronous
    control program, you probably are looking for :ref:`OCSClient<ocs_client>`.

If an asynchronous program containing one or more Clients is required, one can
be implemented using Twisted and :func:`ocs.client_t.run_control_script`. This
is the case if you want to command one Agent from another Agent, since Agents
are written using Twisted.

While OCSClient connects to the crossbar server using HTTP, control programs
using Twisted connect via websockets. When writing a program using Clients that
support Twisted, authors will need to consider their asynchronous paradigm.
When writing a script with the ``ocs.client_t`` module, typically we will define
a function and then run it using :func:`ocs.client_t.run_control_script`. The general
form of our program will be something like::

    import ocs
    from ocs import client_t, site_config

    def my_client_function(app, pargs):
        # Definition and use of Agent Tasks + Processes
        pass

    if __name__ == '__main__':
        parser = site_config.add_arguments()
        parser.add_argument('--target', default="thermo1")
        client_t.run_control_script(my_client_function, parser=parser)

The part we need to write is the body of ``my_client_function``.

To start, each Agent action needs to be defined in a Client before being used.
To do so we need to know what address to reach our Agent at::

    def my_client_function(app, pargs):
        root = 'observatory'

        # Register addresses and operations
        therm_instance = pargs.target
        therm_address = '{}.{}'.format(root, therm_instance)
        therm_ops = {
            'init': client_t.TaskClient(app, therm_address, 'init_lakeshore'),
            'acq': client_t.ProcessClient(app, therm_address, 'acq')
        }

In this code block we define the root of our address space, which by default is
'observatory'. We combine this along with the target defined in
``pargs.target`` to form our address. This target will be the Agent's
"instance-id". We're considering a thermometry control system (either the
Lakeshore 240 or Lakeshore 372) in this example, hence the prefix 'therm'.

We define a dictionary, ``therm_ops``, with each of our Agent Tasks and
Processes, in this case, just one of each. The final argument in both
``client_t.TaskClient`` and ``client_t.ProcessClient`` must match the Task and
Process names registered by the Agent. In this case "init_lakeshore" sets up
the communication with the Lakeshore device, and "acq" begins data acquisition.

To interact with a task we use the keywords "start", "wait", "status", "abort",
and "stop". And since this program runs asynchronously we need to use the
Python keyword "yield"::

    yield therm_ops['init'].start()
    yield therm_ops['init'].wait()
    yield client_t.dsleep(.05)

This will start the "init_lakeshore" task, then wait 0.05 seconds.

.. warning::
    Note the use of ``client_t.dsleep()``, not the common ``time.sleep()``.
    ``time.sleep()`` will "block", disrupting our asynchronous paradigm. For
    more information on this and other subtleties to asynchronous programming, see
    the `autobahn Documentation
    <https://autobahn.readthedocs.io/en/latest/asynchronous-programming.html>`_.

When calling a Process, we just use "start"::

    print("Starting Data Acquisition")
    yield therm_ops['acq'].start()

This will continue running until we command it to stop. Our full Control Program
looks like::

    import ocs
    from ocs import client_t, site_config

    def my_client_function(app, pargs):
        root = 'observatory'

        # Register addresses and operations
        therm_instance = pargs.target
        therm_address = '{}.{}'.format(root, therm_instance)
        therm_ops = {
            'init': client_t.TaskClient(app, therm_address, 'init_lakeshore'),
            'acq': client_t.ProcessClient(app, therm_address, 'acq')
        }

        yield therm_ops['init'].start()
        yield therm_ops['init'].wait()
        yield client_t.dsleep(.05)

        print("Starting Data Acquisition")
        yield therm_ops['acq'].start()


    if __name__ == '__main__':
        parser = site_config.add_arguments()
        parser.add_argument('--target', default="thermo1")
        client_t.run_control_script(my_client_function, parser=parser)
