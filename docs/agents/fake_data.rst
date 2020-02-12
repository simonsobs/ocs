===============
Fake Data Agent
===============

The Fake Data Agent is provided with OCS to help demonstrate and debug issues
with data aggregation and display. It will generate random data and pass it to
an OCS feed.

Command-line / site config args
-------------------------------

.. argparse::
   :module: agents.fake_data.fake_data_agent
   :func: add_agent_args
   :prog: fake_data_agent.py

Agent Operations
----------------

.. autoclass:: agents.fake_data.fake_data_agent.FakeDataAgent
    :members:
