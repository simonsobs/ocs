.. _adding_args:

Adding Agent Arguments
----------------------

Oftentimes you will need to pass some sort of configuration information to the
Agent. For simple configurations (i.e. IP address of a device the Agent
interfaces with) this is done via commandline arguments to the Agent. Within
OCS the argparse module is used for this. This arguments can be written to the
SCF, and will be passed to the Agent automatically at startup.

To start we will add a function to our Agent file to create and ArgumentParser.
Here we define a single argument for our Agent, ``--mode``, which allows us to
select whether the Agent starts in the 'idle' state or in the 'count' state,
which will cause the count Process to run immediately upon startup.

.. code-block:: python

    def add_agent_args(parser_in=None):
        if parser_in is None:
            from argparse import ArgumentParser as A
            parser_in = A()
        pgroup = parser_in.add_argument_group('Agent Options')
        pgroup.add_argument('--mode', type=str, default='count',
                            choices=['idle', 'count'],
                            help="Starting action for the Agent.")
    
        return parser_in

In the ``if __name__ == '__main__':`` block we then add:

.. code-block:: python

    parser = add_agent_args()
    args = site_config.parse_args(agent_class='BarebonesAgent', parser=parser)

    startup = False
    if args.mode == 'count':
        startup = True

Lastly, we modify the registration of the count process:

.. code-block:: python

    agent.register_process(
        'count',
        barebone.count,
        barebone._stop_count,
        startup=startup)

We can now set the ``--mode`` argument in our SCF:

.. code-block::

      {'agent-class': 'BarebonesAgent',
       'instance-id': 'barebones1',
       'arguments': ['--mode', 'idle']},

Agent Code
``````````

Our Agent in full now looks like this:

.. literalinclude:: ../../../agents/barebones_agent/barebones_agent.py
    :language: python

Running the Agent
`````````````````

We can now pass the ``--mode`` argument on the commandline and it will take
precedent over the configuration file:

.. code-block::

    $ python3 barebones_agent.py --mode count
    2022-07-27T01:52:11+0000 Using OCS version 0.9.3
    2022-07-27T01:52:11+0000 Log directory does not exist: /home/<user>/log/ocs/
    2022-07-27T01:52:11+0000 ocs: starting <class 'ocs.ocs_agent.OCSAgent'> @ observatory.barebones1
    2022-07-27T01:52:11+0000 log_file is apparently None
    2022-07-27T01:52:11+0000 transport connected
    2022-07-27T01:52:11+0000 session joined: {'authextra': {'x_cb_node': '7aa0c07345de-1',
                   'x_cb_peer': 'tcp4:172.20.0.1:41912',
                   'x_cb_pid': 11,
                   'x_cb_worker': 'worker001'},
     'authid': '3VRA-35PF-VWRG-GNC9-LA4E-JQT6',
     'authmethod': 'anonymous',
     'authprovider': 'static',
     'authrole': 'iocs_agent',
     'realm': 'test_realm',
     'resumable': False,
     'resume_token': None,
     'resumed': False,
     'serializer': 'msgpack.batched',
     'session': 2822082204009934,
     'transport': {'channel_framing': 'websocket',
                   'channel_id': {},
                   'channel_serializer': None,
                   'channel_type': 'tcp',
                   'http_cbtid': None,
                   'http_headers_received': None,
                   'http_headers_sent': None,
                   'is_secure': False,
                   'is_server': False,
                   'own': None,
                   'own_fd': -1,
                   'own_pid': 36581,
                   'own_tid': 36581,
                   'peer': 'tcp4:127.0.0.1:8001',
                   'peer_cert': None,
                   'websocket_extensions_in_use': None,
                   'websocket_protocol': None}}
    2022-07-27T01:52:11+0000 startup-op: launching count
    2022-07-27T01:52:11+0000 start called for count
    2022-07-27T01:52:11+0000 count:0 Status is now "starting".
    2022-07-27T01:52:11+0000 Starting the count!
    2022-07-27T01:52:11+0000 count:0 Status is now "running".

For more information on ``site_config.parse_args()`` see :ref:`parse_args`.

We are almost done! In the next step we will build a Docker image for the Agent
to facilitate deploying the Agent.
