Adding a Task
-------------

Functionality is added to Agents by adding Tasks and Processes. In this section
we will add a simple Task that simply prints a string passed to it. We do this
by adding a method to the ``BarebonesAgent`` class. The method itself is shown
here:

.. code-block:: python
   :linenos:

    @ocs_agent.param('text', default='hello world', type=str)
    def print(self, session, params):
        """print(text='hello world')

        **Task** - Print some text passed to the Task.

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

        # Print the text provided
        print(f"{params['text']}")

        # Store the text provided in session.data
        session.data = {'text': params['text'],
                        'last_updated': time.time()}

        # bool, 'descriptive text message'
        # True if task succeeds, False if not
        return True, 'Printed text'

Let's look first at the method definition on line 2. We can name the task
function whatever we would like, however Tasks will always have these three
arguments, ``(self, session, params)``. ``self``, because this is a method
within a class, ``session`` is an :class:`ocs.ocs_agent.OpSession` which is
used to track the status, post messages to the message buffer, and pass data to
clients (for more info on this last part see :ref:`session_data`), and
``params`` for all of the arguments that will be passed to the Task (even if
there are none.)

Next, we have the docstring. This generally follows the Google style for Python
docstring supported by napoleon. There are also some conventions for writing
Task docstrings within OCS, which are detailed on the :ref:`documentation`
page.

As described in the docstring, our task has a single argument, ``text``. OCS
provides the ``param`` decorator, which ensures that the required parameters
are passed in and they meet the required checks specified in the decorator. For
details on how to use the decorator see :ref:`param`.

Lastly we have the body of the method, which first sets the status of the Task
to 'running'. When the Task first starts it will automatically get the
'starting' status, and on completion it will have a status indicative of how
the Task completed, i.e. 'failed', 'succeeded'. For other states see
:class:`ocs.base.OpCode`. Next, the code performs the main function of this
task, by printing the text passed in as a parameter. In practice your Agent
will do something much more useful here. The text is then stored in the
``session.data`` object. Again, for more info on using ``session.data``, see
:ref:`session_data`. Lastly, the Task returns, always returning a boolean, with
a string that provides a message that will be inserted into the session message
buffer.

Before a Client on the network can call our Task we must first register the
Task with the crossbar server. This is commonly done outside the Agent after
the Agent is first instantiated. By convention (and for the documentation to
look good) we will keep the method name the same as the name we use to register
the Task with crossbar.

.. code-block:: python

    agent.register_task('print', barebone.print)

Aborting a Task
```````````````
'print' is a very short Task that runs very quickly, however if we have a long
running Task, we might need the ability to stop it before it would normally
complete. OCS supports aborting a Task, however this mechanism needs to be
implemented within the Agent code. This will require adding an aborter
function, which typically will look like this:

.. code-block:: python

    def _abort_print(self, session, params):
        if session.status == 'running':
            session.set_status('stopping')

Within the Task function, at points that are reasonable to request an abort,
you must add a check of the ``session.status`` that then exits the Task if the
status is no longer running. For example:

.. code-block:: python

    if session.status != 'running':
        return False, 'Aborted print'

Where you insert this interrupt code will vary from Agent to Agent. Tasks that
run quickly do not need an abort to be implemented at all. However, for long
running Tasks abort should be implemented.

When registering the Task, the aborter must be specified:

.. code-block:: python

    agent.register_task('print', barebone.print, aborter=barebone._abort_print)

.. note::

    By default the aborter will run in the same threading pattern as the task.
    If your Task runs in the main reactor (i.e. is decorated with
    ``@inlineCallbacks``), then the aborter should also run in the reactor, and so
    needs to ``yield`` at the end of the method. In our example this would look
    like:

    .. code-block:: python

        @inlineCallbacks
        def _abort_print(self, session, params):
            if session.status == 'running':
                session.set_status('stopping')
            yield

Again, since 'print' runs quickly, we do not implement an aborter for it here.
For an example of an abortable task, see
:func:`ocs.agents.fake_data.agent.FakeDataAgent.delay_task`.

Agent Code
``````````

Our full Agent so far should look like this:

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
        """

        def __init__(self, agent):
            self.agent = agent

        @ocs_agent.param('text', default='hello world', type=str)
        def print(self, session, params):
            """print(text='hello world')

            **Task** - Print some text passed to the Task.

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

            # Print the text provided
            print(f"{params['text']}")

            # Store the text provided in session.data
            session.data = {'text': params['text'],
                            'last_updated': time.time()}

            # bool, 'descriptive text message'
            # True if task succeeds, False if not
            return True, 'Printed text'


    def main(args=None)
        args = site_config.parse_args(agent_class='BarebonesAgent', args=args)
        agent, runner = ocs_agent.init_site_agent(args)
        barebone = BarebonesAgent(agent)
        agent.register_task('print', barebone.print)
        runner.run(agent, auto_reconnect=True)


    if __name__ == '__main__':
        main()


Running the Agent
`````````````````

We can now run our Agent and interact with it via a Client. First, start the
Agent:

.. code-block::

    $ OCS_CONFIG_DIR=/path/to/your/ocs-site-config/ ocs-agent-cli --agent barebones_agent.py --entrypoint main --instance-id barebones1
    Args: ['--instance-id', 'barebones1']
    2022-07-22T10:55:46-0400 Using OCS version 0.9.3+3.gfc30f3d.dirty
    2022-07-22T10:55:46-0400 ocs: starting <class 'ocs.ocs_agent.OCSAgent'> @ observatory.barebones1
    2022-07-22T10:55:46-0400 log_file is apparently None
    2022-07-22T10:55:46-0400 transport connected
    2022-07-22T10:55:46-0400 session joined:
    SessionDetails(realm="test_realm",
                   session=3109556471169828,
                   authid="RJ9J-EP5Y-LP5H-RSWC-GCLW-LSRJ",
                   authrole="iocs_agent",
                   authmethod="anonymous",
                   authprovider="static",
                   authextra={'x_cb_node': '7eedf90409d6-1', 'x_cb_worker': 'worker001', 'x_cb_peer': 'tcp4:192.168.240.1:33046', 'x_cb_pid': 16},
                   serializer="cbor.batched",
                   transport="websocket",
                   resumed=None,
                   resumable=None,
                   resume_token=None)

Next, run a Client, calling the print task:

.. code-block::

    $ OCS_CONFIG_DIR=/path/to/your/ocs-site-config/ python3
    Python 3.10.5 (main, Jun  6 2022, 18:49:26) [GCC 12.1.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ocs.ocs_client import OCSClient
    >>> client = OCSClient('barebones1')
    >>> client.print.start()
    OCSReply: OK : Started task "print".
      print[session=0]; status=starting for 0.003074 s
      messages (1 of 1):
        1658501763.027 Status is now "starting".
      other keys in .session: op_code, data
    >>> client.print.status()
    OCSReply: OK : Session active.
      print[session=0]; status=done without error 3.7 s ago, took 0.001974 s
      messages (4 of 4):
        1658501763.027 Status is now "starting".
        1658501763.028 Status is now "running".
        1658501763.029 Printed text
        1658501763.029 Status is now "done".
      other keys in .session: op_code, data

In the terminal running your Agent you should see:

.. code-block::

    2022-07-22T10:56:03-0400 start called for print
    2022-07-22T10:56:03-0400 print:0 Status is now "starting".
    2022-07-22T10:56:03-0400 hello world
    2022-07-22T10:56:03-0400 print:0 Status is now "running".
    2022-07-22T10:56:03-0400 print:0 Printed text
    2022-07-22T10:56:03-0400 print:0 Status is now "done".
