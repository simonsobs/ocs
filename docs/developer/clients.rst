.. highlight:: python

.. _clients:

Clients
=======
Multi-Agent interactions are orchestrated by OCS Clients. Clients can be
written in any language supported by crossbar, however most commonly these will
be written in Python or Javascript. This page focuses on writing an OCS Client
in Python.

There are two ways to write a Python OCS Client, one (we'll call it a Basic
Client) uses `ocs.client_t`, the other (called a Matched Client) uses
`ocs.matched_client`. Generally, a Matched Client is going to be easier to
write (and is the newer of the two methods), but for completeness we document
both methods.

The clients differ in how they communicate with the crossbar server. Writers of
Basic Clients need to consider their asynchronous paradigm.

Basic Clients
-------------
We write a basic Client with the `ocs.client_t` module. Typically we will
define a function and then run it using `ocs.client_t.run_control_script2`. The
general form of our Client will be something like::

    import ocs 
    from ocs import client_t, site_config
    
    def my_client_function(app, pargs):
        # Definition and use of Agent Tasks + Processes
        pass
    
    if __name__ == '__main__':
        parser = site_config.add_arguments()
        parser.add_argument('--target', default="thermo1")
        client_t.run_control_script2(my_client_function, parser=parser)

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

In this codeblock we define the root of our address space, which by default is
'observatory'. We combine this along with the target defined in
``pargs.target`` to form our address. This target will be the Agent's
"instance-id". We're considering a thermometry control system (either the
Lakeshore 240 or Lakeshore 372) in this example, hence the prefix 'therm'.

We define a dictionary, ``therm_ops``, with each of our Agent Tasks and
Processes, in this case, just one of each. The final arguement in both
``client_t.TaskClient`` and ``client_t.ProcessClient`` must match the Task and
Process names registered by the Agent. In this case "init_lakeshore" sets up
the communication with the Lakeshore device, and "acq" begins data acquisition.

To interact with a task we use the keywords "start", "wait", "status", "abort",
and "stop". And since basic Clients run asynchronously we need to use the
Python keyword "yield"::

    yield therm_ops['init'].start()
    yield therm_ops['init'].wait()
    yield client_t.dsleep(.05)

This will start the "init_lakeshore" task, then wait 0.05 seconds.

.. warning::
    Note the use of ``client_t.dsleep()``, not the common ``time.sleep()``.
    ``time.sleep()`` will "block", disrupting our asynchronus paradigm. For
    more information on this and other subtleties to asynchronus programming, see
    the `autobahn Documentation
    <https://autobahn.readthedocs.io/en/latest/asynchronous-programming.html>`_.

When calling a Process, we just use "start"::

    print("Starting Data Acquisition")
    yield therm_ops['acq'].start()

This will continue running until we command it to stop. We will do so in the
Matched Client example. So our full Basic Client looks like::

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
        client_t.run_control_script2(my_client_function, parser=parser)


Matched Clients
---------------
A Matched Client performs the definition of Agent tasks and processes within
the Client for us, a great convenience when our Agents have many Tasks and
Processes registered. The Matched Client also makes its calls over http and
avoids some of the potentially unfamiliar use of ``yield``.

An example MatchedClient would look like this::

    from ocs.matched_client import MatchedClient
    
    therm_client = MatchedClient('thermo1')

The returned object, ``therm_client``, is populated with attributes
for each Task and Process exposed by the OCS Agent with the specified
``instance-id`` (in this case ``thermo1``).  We then can call
different Task and Process methods, using the syntax
*client-name.op-name.method(kwargs...)*. For example, to stop a data
acquisition Process called ``acq``::

    therm_client.acq.stop()

So our full MatchedClient to stop a running acquisition process on "thermo1" is
just three lines::

    from ocs.matched_client import MatchedClient
    
    therm_client = MatchedClient('thermo1')
    therm_client.acq.stop()

Each attribute of therm_client is an instance of either
``MatchedProcess`` or ``MatchedTask``.  These objects expose the
methods appropriate for their Operation type; they both support
``start(**kwargs)`` and ``status()`` but only ``MatchedProcess``
supports ``stop()`` and only ``MatchedTask`` supports ``abort()``.

The ``MatchedProcess`` and ``MatchedTask`` instances are also,
themselves, callable.  If a ``MatchedProcess`` is called directly, it
is equivalent to running the ``.status()`` method::

    # Because ``acq`` is a Process, these two are equivalent:
    result = therm_client.acq()
    result = therm_client.acq.status()

If a ``MatchedTask`` is called directly it is equivalent to running
``.start()`` followed by ``.wait()``::

    # Because ``init`` is a Task, this line:
    result = therm_client.init(auto_acquire=True)

    # ... is equivalent to these lines:
    result = therm_client.init.start(auto_acquire=True)
    if result[0] == ocs.OK:
        result = therm_client.init.wait()


For comparison to the Basic Client, an equivalent Matched Client to the Basic
Client example would be::

    import time
    from ocs.matched_client import MatchedClient
    
    therm_client = MatchedClient('thermo1')
    therm_client.init()
    time.sleep(.05)

    therm_client.acq.start()

.. _op_replies:

Replies from Operation methods
------------------------------

The responses from Operation methods is a tuple, (status, message,
session).  The elements of the tuple are:

  ``status``
    An integer value equal to ocs.OK, ocs.ERROR, or ocs.TIMEOUT.

  ``message``
    A string providing a brief description of the result (this is
    normally pretty boring for successful calls, but might contain a
    helpful tip in the case of errors).

  ``session``
    The session information... see below.

Responses obtained from MatchedClient calls are lightly wrapped by
class ``OCSReply`` so that ``__repr__`` produces a nicely formatted
description of the result.  For example::

  >>> c.set_autoscan.wait()
  OCSReply: OK : Operation "set_autoscan" just exited.
    set_autoscan[session=7]; status=done without error 30.6 s ago, took 0.113400 s
    messages (4 of 4):
      1585667844.423 Status is now "starting".
      1585667844.424 Status is now "running".
      1585667844.535 Set autoscan to True
      1585667844.536 Status is now "done".
    other keys in .status: data


The ``session`` portion of the reply is dictionary containing a bunch
of potentially useful information.  This information corresponds to
the OpSession maintained by the OCSAgent class for each run of an
Agent's Operation (see OpSession in ocs/ocs_agent.py):

  ``'session_id'``
    An integer identifying this run of the Operation.  If an Op ends
    and is started again, ``session_id`` will be different.

  ``'op_name'``
    The operation name.  You probably already know this.

  ``'status'``
    A string representing the state of the operation.  The possible
    values are 'starting', 'running', 'done'.

  ``'start_time'``
    The timestamp corresponding to when this run was started.

  ``'end_time'``
    If ``status`` == ``'done'``, then this is the timestamp at which
    the run completed.  Otherwise it will be None.

  ``'success'``
    If ``status`` == ``'done'``, then this is a boolean indicating
    whether the operation reported that it completed successfully
    (rather than with an error).

  ``'data'``
    Agent-specific data that might of interest to a user.  This may be
    updated while an Operation is running, but once ``status`` becomes
    ``'done'`` then ``data`` should not change any more.  A typical
    use case here would be for a Process that is monitoring some
    system to report the current values of key parametrs.  This should
    not be used as an alternative to providing a data feed... rather
    it should provide current values to answer immediate questions.

  ``'messages'``
    A list of Operation log messages.  Each entry in the list is a
    tuple, (timestamp, text).

