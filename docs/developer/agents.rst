Agents
======

In OCS, Agents are the software programs that contain the information you need
to do something useful. Agents can be used to communicate with hardware, or to
perform functions on preexisting data files. This guide will teach you how to
write a basic agent that can publish data to a feed.

.. note::

    Throughout this guide we will reference a core ocs Agent, "FakeDataAgent",
    which generates random data for testing parts of OCS. We will reproduce
    sections of code here with slight modifications to demonstrate certain
    features. The full, unmodified, agent code is accessible on `GitHub
    <https://github.com/simonsobs/ocs/blob/develop/agents/fake_data/fake_data_agent.py>`_.

.. toctree::
    :maxdepth: 2

    agents/agents
    agents/parameters
    agents/locking
    agents/logging
    agents/documentation
