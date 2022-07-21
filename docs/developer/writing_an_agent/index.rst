.. _writing_an_agent:

Writing an Agent
================

Agents are one of the primary components of OCS. They are long running software
servers that make Tasks and Processes (i.e. functions) available to OCS Clients
on the network. They can also send data across the network via OCS Feeds. This
guide will teach you how to write a basic Agent that contains one Task and one
Process and can publish data to a Feed.

.. note::

    Throughout this guide we will run our Agent. We assume you have OCS
    installed, have followed the :ref:`quickstart` guide, have at least a
    crossbar server running, and an OCS site config file that we can add our
    Agent configuration to.

.. toctree::
    :maxdepth: 1

    minimum
    task
    process
    logging
    timeoutlock
    publish
    arguments
    docker
    next

