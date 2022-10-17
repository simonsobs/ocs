Minimum Agent Structure
-----------------------

Agents take the form of Python classes, which take an OCSAgent object as their
first argument. The following code shows the absolute bare minimum needed for
an Agent to run:

.. code-block:: python

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


    def main(args=None):
        args = site_config.parse_args(agent_class='BarebonesAgent', args=args)
        agent, runner = ocs_agent.init_site_agent(args)
        barebone = BarebonesAgent(agent)
        runner.run(agent, auto_reconnect=True)


    if __name__ == '__main__':
        main()

While this has no useful functionality, we can still run the Agent and see it
connect to the crossbar server. First add this configuration block to your SCF::

    {'agent-class': 'BarebonesAgent',
     'instance-id': 'barebones1',
     'arguments': []},

Here the 'agent-class' much match the class we define within the Agent and the
'instance-id' can be anything, but needs to be unique among all the Agents on
your network. The 'arguments' list is a place to pass any commandline arguments
to your Agent, typically just those you define for your Agent (which we will
get to in :ref:`adding_args`.)

The structure here for setting up an entrypoint function, ``main()``, that
takes ``args`` as an argument, is important to how ``ocs-agent-cli`` and
:ref:`OCS Plugins <ocs_plugins>` function. You can use a different name other
than "main" for the entrypoint function name, but the ``args`` argument must
still be present.

Next, run the Agent directly using ``ocs-agent-cli``:

.. code-block:: bash

    $ OCS_CONFIG_DIR=/path/to/your/ocs-site-config/ ocs-agent-cli --agent barebones_agent.py --entrypoint main --instance-id barebones1
    Args: ['--instance-id', 'barebones1']
    2022-07-21T15:02:30-0400 Using OCS version 0.9.3+1.g48026a2.dirty
    2022-07-21T15:02:30-0400 ocs: starting <class 'ocs.ocs_agent.OCSAgent'> @ observatory.barebones1
    2022-07-21T15:02:30-0400 log_file is apparently None
    2022-07-21T15:02:30-0400 transport connected
    2022-07-21T15:02:30-0400 session joined:
    SessionDetails(realm="test_realm",
                   session=5205672040875670,
                   authid="JJ3M-WWE6-NTR4-643M-RU5Q-S96H",
                   authrole="iocs_agent",
                   authmethod="anonymous",
                   authprovider="static",
                   authextra={'x_cb_node': '7eedf90409d6-1', 'x_cb_worker': 'worker001', 'x_cb_peer': 'tcp4:192.168.240.1:52470', 'x_cb_pid': 16},
                   serializer="cbor.batched",
                   transport="websocket",
                   resumed=None,
                   resumable=None,
                   resume_token=None)

.. note::
    While we encourage the use of ``ocs-agent-cli`` the Agent could be run directly via::

        $ OCS_CONFIG_DIR=/path/to/your/ocs-site-config/ python3 barebones_agent.py

    We will continue to use ``ocs-agent-cli`` throughout this guide.

We see some informative messages about the ocs version, the OCS Agent's address
(observatory.barebones1), the log file (unset in this example), and then we see
the Agent connecting to the crossbar server.

In the following pages we will fill out the functionality of our Agent. Each
page will describe a change to be made to the Agent, then display the full
Agent code with all changes so far followed by an example of running the Agent.
First up is adding a Task to the Agent.
