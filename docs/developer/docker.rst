.. _dockerizing_agent_or_plugin:

Docker
======

OCS Agents are commonly deployed in Docker containers. OCS provides a base
Docker image, which contains the dependencies required to run OCS and all of
the core agents. This page describes the details of this image, and how to
build upon it to deploy your Agent(s) or OCS plugin.

OCS Base Image
--------------

The OCS base image is built from the `Dockerfile
<https://github.com/simonsobs/ocs/blob/develop/Dockerfile>`_ in the root of the
respository, shown here:

.. literalinclude:: ../../Dockerfile
    :language: docker

This file describes the steps taken to build the base image. This includes
configuring an ocs user, creating a directory to store data from the
aggregator, setting up the configuration file directory, installing
dependencies, installing ocs, and setting the default entrypoint to launch an
OCS Agent via ``ocs-agent-cli``. See the `Dockerfile reference
<https://docs.docker.com/engine/reference/builder/>`_ in the Docker
documentation for more information about how to write a Dockerfile.

Building Upon the Base Image
----------------------------

When writing an OCS Agent (or plugin) you can build upon this OCS base image to
deploy your Agent (or plugin). To do so you would write a new ``Dockerfile``
that looks something like:

.. code-block:: docker

    # my-ocs-agent-docker
    # A brief description of your image.
    
    # Use the ocs image as a base
    FROM simonsobs/ocs:latest
    
    # Install required dependencies
    RUN apt-get update && apt-get install -y rsync \
        wget \
        python3-pip
    
    # Copy in and install requirements
    COPY requirements.txt /app/my-ocs-agent/requirements.txt
    WORKDIR /app/my-ocs-agent/
    RUN pip3 install -r requirements.txt
    
    # Copy the current directory contents into the container at /app
    COPY . /app/my-ocs-agent/
    
    # Install my-ocs-agent
    RUN pip3 install .
    
    # Run agent on container startup
    ENTRYPOINT ["dumb-init", "ocs-agent-cli"]

This assumes you have a ``requirements.txt`` file for any additional
dependencies for your Agent, and that you have a package to install, like an
OCS plugin.

.. note::

    Properities of the parent image are inherited, for example
    ``OCS_CONFIG_DIR`` will still be configured as it was in the OCS base image
    unless otherwise changed in your ``Dockerfile``.

This image now includes all the dependencies you need to run your Agent and you
can move on to using the image. This is commonly done with Docker Compose, as
described in the following section.

Using An OCS Image
------------------

Whether you are using the OCS base image to run a core agent or using an image
you have made to extend the functionality of OCS with your own Agent or plugin
you can configure the image to run using Docker Compose. For example, using the
base image to run a core agent would look something like:

.. code-block:: yaml

    ocs-agent:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro
        environment:
          - INSTANCE_ID=registry

Environment variables used to configure the Agent are listed in the following table:

.. list-table:: Docker Environment Variables
   :widths: 25 25 50
   :header-rows: 1

   * - Variable
     - CLI Equivalent
     - Description
   * - ``INSTANCE_ID``
     - ``--instance-id``
     - Agent instance-id, e.g. ``aggregator``
   * - ``SITE_HUB``
     - ``--site-hub``
     - WAMP server address, e.g. ``ws://10.10.10.10:8001/ws``
   * - ``SITE_HTTP``
     - ``--site-http``
     - WAMP server HTTP address, e.g. ``http://10.10.10.10:8001/call``

Any additional flags needed can be added using ``command``. This includes if
you need to run a one-off Agent that is not apart of an OCS plugin. This would
add the following lines to your ``docker-compose.yaml`` service configuration:

.. code-block:: yaml

    command:
      - '--agent /app/my-ocs-agent/agent.py --entrypoint main'

.. note::

    Arguments passed on the commandline (or in the ``command`` block of your
    configuration) take precedent over any settings set via environment variables.

For more specific examples on how to use each Agent, see the Agent's reference
page in the sidebar.
