.. highlight:: rst

.. _template:

==============
Template Agent
==============

# A brief description of the Agent.

.. argparse::
   :module: agents.template.template_agent
   :func: make_parser
   :prog: template_agent.py

Dependencies
------------

# Any external dependencies for agent. Omit if there are none, or they are
# included in the main requirements.txt file.

Configuration File Examples
---------------------------

Below are configuration examples for the ocs config file and for running the
Agent in a docker container.

OCS Site Config
````````````````

An example site-config-file block::

    {'agent-class': 'TemplateAgent',
       'instance-id': 'template',
       'arguments': [['--argument-1', 'value1'],
                     ['--argument-2', 42],
                     ['--argument-3']]},

Docker Compose
``````````````

An example docker-compose configuration::

    ocs-template:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        environment:
          - LOGLEVEL=info
          - INSTANCE_ID=template
          - SITE_HUB=ws://10.10.10.2:8001/ws
          - SITE_HTTP=http://10.10.10.2:8001/call
        volumes:
          - ${OCS_CONFIG_DIR}:/config

Description
-----------

# Detailed description of the Agent. Include any details the users or developers
# might find valuable.

Subsection
``````````

# Use subsections where appropriate.

Agent API
---------

# Autoclass the Agent, this is for users to reference when writing clients.

.. autoclass:: agents.template.template_agent.TemplateAgent
    :members:

Example Clients
---------------

# If an example client makes use of the Agent more clear, include here in a code block::

    from ocs.ocs_client import OCSClient
    client = OCSClient('template')
    client.task()

Supporting APIs
---------------

# Autodoc any code supporting the Agent. This is for developers to reference
# when working on the Agent. :noindex: should be used here if code is also
# indexed in the main API page.

.. autoclass:: ocs.agent.template.Template1
    :members:
    :noindex:

.. autoclass:: ocs.agent.template.Template2
    :members:
    :noindex:
