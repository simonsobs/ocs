.. highlight:: rst

Configuration
=============

Next we need to configure both the `docker-compose` and `ocs` environments,
each with their own configuration files. These files will differ for each site
depending on your hardware setup. Below we cover a simple configuration for
each. Later we discuss more advanced configuration.

docker-compose.yaml
-------------------

Docker is used extensively in deploying several parts of the live monitor.
Docker Compose is used to manage all the containers required to run the live
monitor software. The Docker Compose configuration file defines the containers
that we will control.

The ocs site configs templates provide two templates for
this file, one for production use, and one for development. If you are in doubt
of which to pick, use the production one. The file should be renamed to
``docker-compose.yaml``, as this is the default file parsed by
``docker-compose``. A configuration file can also be specified with the ``-f``
flag.

The template configuration does not contain all available containers.  Details
about more containers can either be found in the `sisock documentation`_ or in
the socs and ocs documentation.

.. _`sisock documentation`: https://grumpy.physics.yale.edu/docs/sisock/

The template ``docker-compose.yml`` file, looks something like this::

    version: '2'
    volumes:
      grafana-storage:
        external: true
    services:
      # --------------------------------------------------------------------------
      # Grafana for the live monitor.
      # --------------------------------------------------------------------------
      grafana:
        image: grafana/grafana:5.4.0
        restart: always
        ports:
          - "127.0.0.1:3000:3000"
        environment:
          - GF_INSTALL_PLUGINS=grafana-simple-json-datasource, natel-plotly-panel
        volumes:
          - grafana-storage:/var/lib/grafana

      # --------------------------------------------------------------------------
      # sisock Components
      # --------------------------------------------------------------------------
      sisock-crossbar:
        image: grumpy.physics.yale.edu/sisock-crossbar:latest
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        volumes:
          - ./.crossbar:/app/.crossbar
        environment:
             - PYTHONUNBUFFERED=1

      sisock-http:
        image: grumpy.physics.yale.edu/sisock-http:latest
        depends_on:
          - "sisock-crossbar"
        volumes:
          - ./.crossbar:/app/.crossbar:ro

      weather:
        image: grumpy.physics.yale.edu/sisock-weather-server:latest
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"
        volumes:
          - ./.crossbar:/app/.crossbar:ro

      # --------------------------------------------------------------------------
      # sisock Data Servers
      # --------------------------------------------------------------------------
      LSA23JD:
        image: grumpy.physics.yale.edu/sisock-thermometry-server:latest
        environment:
            TARGET: LSA23JD # match to instance-id of agent to monitor
            NAME: 'LSA23JD' # will appear in sisock a front of field name
            DESCRIPTION: "LS372 in the Bluefors control cabinet."
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"

      # --------------------------------------------------------------------------
      # OCS Agents
      # --------------------------------------------------------------------------
      ocs-registry:
        image: grumpy.physics.yale.edu/ocs-registry-agent:latest
        hostname: ocs-docker
        volumes:
          - /home/so_user/git/ocs-site-configs/yale/prod/:/config:ro
        depends_on:
          - "sisock-crossbar"

      ocs-aggregator:
        image: grumpy.physics.yale.edu/ocs-aggregator-agent:latest
        hostname: ocs-docker
        user: "9000"
        volumes:
          - /home/so_user/git/ocs-site-configs/yale/prod/:/config:ro
          - "/data:/data"
        depends_on:
          - "sisock-crossbar"

.. note::

    Bind mounts are a system unique property. This is especially true for ones
    which use absolute paths, for instance the volumes defined for the OCS Agent
    containers. These will need to be updated for your system.

Understanding what is going on in this configuration file is key to getting a
system that is working smoothly. The Docker Compose reference_ explains the
format of the file, for details on syntax you are encouraged to check the
official documentation.

In the remainder of this section we will go over our example. We first define
the use of an external docker volume, ``grafana-storage``, which we created
using the ``init-docker-env.sh`` script.

Every block below ``services:`` defines a Docker container. Let's look at one
example container configuration. This example does not represent something we
would want to actually use, but contains configuration lines relevant to many
other container configurations::

  g3-reader:
    image: grumpy.physics.yale.edu/sisock-g3-reader-server:latest
    restart: always
    hostname: ocs-docker
    user: "9000"
    ports:
      - "127.0.0.1:8001:8001" # expose for OCS
    volumes:
      - /data:/data:ro
      - ./.crossbar:/app/.crossbar
    environment:
        MAX_POINTS: 1000
        SQL_HOST: "database"
        SQL_USER: "development"
        SQL_PASSWD: "development"
        SQL_DB: "files"
    depends_on:
      - "sisock-crossbar"
      - "sisock-http"
      - "database"

The top line, ``g3-reader``, defines the name of the service to docker-compose.
These must be unique. ``image`` defines the docker image used for the
container. A container can be thought of as a copy of an image. The container
is what actually runs when you startup your docker service. ``restart`` allows
you to define when a container can be automatically restarted, in this
instance, always. ``hostname`` defines the hostname internal to the container.
This is used in the OCS container configurations in conjunction with the
ocs-site-configs file. ``user`` defines the user used inside the container.
This is only used on the aggregator agent configuration.

``ports`` defines the ports exposed from the container to the host. This is
used on containers like the crossbar container and the grafana container.
``volumes`` defines mounted docker volumes and bind mounts to the host system.
The syntax here is ``/host/system/path:/container/system/path``. Alternatively
the host system path can be a named docker container, like the one used for
grafana. ``environment`` defines environment variables inside the container.
This is used for configuring behaviors inside the containers. ``depends_on``
means Docker Compose will wait for the listed containers to start before
starting this container. This does not mean the services will be ready, but the
container will be started.

For more details on configurations for individual containers, see the service
documentation pages, for instance in the `sisock documentation`_ or in the
respective ocs agent pages.

.. _reference: https://docs.docker.com/compose/compose-file/compose-file-v2/
.. _sisock: https://github.com/simonsobs/sisock

OCS
---
OCS has a separate configuration file which defines connection parameters for
the crossbar server, as well as the Agents that will run on each host, whether
they are on the host system, or in a Docker container. This configuration file
allows default startup parameters to be defined for each Agent.

We will look at a simple example and describe how deploying Agents in
containers should be handled. For more details on the OCS site configuration
file see :ref:`site_config`. Here is an example config::

    # Site configuration for a fake observatory.
    hub:

      wamp_server: ws://localhost:8001/ws
      wamp_http: http://localhost:8001/call
      wamp_realm: test_realm
      address_root: observatory
      registry_address: observatory.registry

    hosts:

        ocs-docker: {

            'agent-instances': [
                # Core OCS Agents
                {'agent-class': 'RegistryAgent',
                 'instance-id': 'registry',
                 'arguments': []},
                {'agent-class': 'AggregatorAgent',
                 'instance-id': 'aggregator',
                 'arguments': [['--initial-state', 'record'],
                               ['--time-per-file', '3600'],
                               ['--data-dir', '/data/']]},

                # Lakeshore agent examples
                {'agent-class': 'Lakeshore372Agent',
                 'instance-id': 'LSA22YE',
                 'arguments': [['--serial-number', 'LSA22YE'],
                               ['--ip-address', '10.10.10.4']]},

                {'agent-class': 'Lakeshore240Agent',
                 'instance-id': 'LSA22Z2',
                 'arguments': [['--serial-number', 'LSA22Z2'],
                               ['--num-channels', 8]]},
            ]
        }

The `hub` section defines the connection parameters for the crossbar server.
This entire section will likely remain unchanged, unless you are running a site
with multiple computers, in which case other computers will need to either run
their own crossbar server, or point to an already configured one.

Under `hosts` we have defined a single host, `ocs-docker`. This configuration
example shows an example where every OCS Agent is running within a Docker
container. The hostname `ocs-docker` must match that given to your docker
containers in the ``docker-compose.yaml`` file. We recommend naming the docker
hosts based on your local hostname, however the configuration shown here will
also work on a simple site layout.

.. note::
    To determine your host name, open a terminal and enter ``hostname``.

Each item under a given host describes the OCS Agents which can be run. For
example look at the first 372 Agent::

          {'agent-class': 'Lakeshore372Agent',
           'instance-id': 'LSA22YE',
           'arguments': [['--serial-number', 'LSA22YE'],
                         ['--ip-address', '10.10.10.4']]},

The ``agent-class`` is given by the actual Agent which will be running. This
must match the name defined in the Agent's code. The ``instance-id`` is a
unique name given to this agent instance. Here we use the Lakeshore 372 serial
number, `LSA22YE`. This will need to be noted for later use in the live
monitoring. Finally the arguments are used to pass default arguments to the
Agent at startup, which contains the serial number again as well as the IP
address of the 372.
