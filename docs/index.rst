Observatory Control System
==========================

The Observatory Control System is a distributed control system designed to
coordinate data acquisition in astronomical observatories.

This documentation is split into three main sections. First, the User Guide.
This is for users who want to configure and run a system controlled by OCS.
Next, the Agent Reference. This section covers each OCS Agent and how to
configure them. Finally, the Developer Guide. These pages are for those who
want to understand more of what goes on within OCS, and for those looking to
write OCS Agents or Clients.

.. toctree::
    :caption: User Guide
    :maxdepth: 3

    user/intro
    user/dependencies
    user/installation
    user/quickstart
    user/configuration
    user/network
    user/logging
    user/ocs_web
    user/cli_tools
    user/ocs_util


.. toctree::
    :caption: Agent Reference
    :maxdepth: 3

    agents/aggregator
    agents/influxdb_publisher
    agents/registry
    agents/fake_data
    agents/host_manager


.. toctree::
    :caption: Developer Guide
    :maxdepth: 3

    developer/architecture
    developer/site_config
    developer/agents
    developer/clients
    developer/data
    developer/web
    developer/testing


.. toctree::
    :caption: API Reference
    :maxdepth: 2

    api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
