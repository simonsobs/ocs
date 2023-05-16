.. highlight:: rst

Docker Configuration
=====================

Once we've configured the ocs site config file we need to define our Docker
environment. We do that with a `docker-compose.yaml` file. We recommend you
keep these files together, in a version controlled repository. These files will
differ for each site depending on your hardware setup. Below we cover a simple
configuration.

docker-compose.yaml
-------------------

Docker Compose is used to manage all the containers required to run OCS. The
Docker Compose configuration file defines the containers that we will control.

.. note::
    The filename is important here, as the `docker-compose.yaml` path is the
    default one parsed by the docker-compose tool. A configuration file can be
    specified with the `-f` flag.

Details about configuring individual Agents can be found in the Agent Reference
section of this documentation. An example `docker-compose.yaml` file looks
something like this (note this does not contain all possibly configured
components)::

    version: '3.7'
    volumes:
      grafana-storage:

    services:
      # --------------------------------------------------------------------------
      # Grafana for the live monitor.
      # --------------------------------------------------------------------------
      grafana:
        image: grafana/grafana:latest
        restart: always
        ports:
          - "127.0.0.1:3000:3000"
        volumes:
          - grafana-storage:/var/lib/grafana

      # InfluxDB Backend for Grafana
      influxdb:
        image: influxdb:1.7
        container_name: "influxdb"
        restart: always
        ports:
          - "8086:8086"
        environment:
          - INFLUXDB_HTTP_LOG_ENABLED=false
        volumes:
          - /srv/influxdb:/var/lib/influxdb

      # --------------------------------------------------------------------------
      # Crossbar
      # --------------------------------------------------------------------------
      crossbar:
        image: simonsobs/ocs-crossbar:latest
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        environment:
          - PYTHONUNBUFFERED=1

      # --------------------------------------------------------------------------
      # OCS Agents
      # --------------------------------------------------------------------------
      ocs-aggregator:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        user: "9000"
        environment:
          - INSTANCE_ID=aggregator
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro
          - "/data:/data"
        depends_on:
          - "crossbar"

      ocs-influx-publisher:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        environment:
          - INSTANCE_ID=influxagent
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro

      ocs-LSA99ZZ:
        image: simonsobs/ocs-lakeshore372-agent:latest
        hostname: grumpy-docker
        network_mode: "host"
        environment:
          - INSTANCE_ID=LSA99ZZ
          - SITE_HUB=ws://10.10.10.2:8001/ws
          - SITE_HTTP=http://10.10.10.2:8001/call
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro


.. warning::

    Bind mounts are a system unique property. This is especially true for ones
    which use absolute paths. If they exist in any reference configuration
    file, they will need to be updated for your system.

Understanding what is going on in this configuration file is key to getting a
system that is working smoothly. The Docker Compose reference_ explains the
format of the file, for details on syntax you are encouraged to check the
official documentation.

In the remainder of this section we will go over our example. The first line
defines the version of the docker-compose file format, which corresponds to the
Docker Engine version you are running. You likely do not have to change this,
unless you need a new feature available in a more recent version.

Every block below ``services:`` defines a Docker container. Let's look at one
example container configuration. This example does not represent something we
would want to actually use, but contains configuration lines relevant to many
other container configurations::

  example-container-name:
    image: simonsobs/example-docker-image:latest
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
        SQL_DB: "files"
    depends_on:
      - "crossbar"
      - "database"

The top line, ``example-container-name``, defines the name of the service to
docker-compose. These must be unique. ``image`` defines the docker image used
for the container. Associated with the image is the image tag, in this case
"latest". This defines the version of the image. A container can be thought of
as a copy of an image. The container is what actually runs when you startup
your docker service. ``restart`` allows you to define when a container can be
automatically restarted, in this instance, always. ``hostname`` defines the
hostname internal to the container. This is used in the OCS container
configurations in conjunction with the ocs-site-configs file. We recommend
appending "-docker" to the hostname to distinguish Agents running within
containers from those running directly on the host. ``user`` defines the user
used inside the container. This is only used on the aggregator agent
configuration.

.. warning::
    Pay attention to your version tags. "latest" is a convention in Docker to
    roughly mean the "most up to date" image. It is the default if a tag is
    left off. However, the "latest" image is subject to change. Pulling a "latest"
    version today will not be guaranteed to get you the same image at another time.

    What this means is for reproducability of your deployment, and perhaps for
    your own sanity, we recommend you use explicit version tags. Tags can be
    identified on an image's Docker Hub page.

``ports`` defines the ports exposed from the container to the host. This is
used on containers like the crossbar container and the grafana container.
``volumes`` defines mounted docker volumes and bind mounts to the host system.
The syntax here is ``/host/system/path:/container/system/path``. Alternatively
the host system path can be a named docker volume, in which case docker manages
the storage. ``environment`` defines environment variables inside the
container. This is used for configuring behaviors inside the containers.
``depends_on`` means Docker Compose will wait for the listed containers to
start before starting this container. This does not mean the services will be
ready, but the container will be started.

.. note::
    Environment variables can be used within a docker-compose configuration
    file. This is done for the `OCS_CONFIG_DIR` mount for the OCS agents in the
    default template.  For more information see the `docker compose
    documentation`_.

    If you use this functionality, be aware that environment variables must be
    explicitly passed to sudo via the ``-E`` flag, for example: ``$ sudo -E
    docker-compose up -d``

For more details on configurations for individual containers, see the service
documentation pages, for instance in the Agent Reference section.

.. _reference: https://docs.docker.com/compose/compose-file/compose-file-v2/
.. _`docker compose documentation`: https://docs.docker.com/compose/environment-variables/

Considerations for Deployment
-----------------------------
The above examples are simple and meant to get you running quickly. However,
they might not be the best configuration for deployment. One inconvenient thing
is everything is managed in a single ``docker-compose.yml`` file. This means
when you bring the system down, or restart it, all components are shutdown,
this includes Grafana, which is one thing you might want running all the time,
even if not actively collecting data with OCS, since you might want to look at
past data. To achieve this you can separate the long-running services to
different configuration files in separate directories, for instance::

    .
    ├── default.yaml
    ├── docker-compose.yml
    ├── influxdb
    │   └── docker-compose.yml
    └── crossbar
        └── docker-compose.yml

Where the separate compose files would look something like::

    # influxdb/docker-compose.yml
    version: '3.7'
    networks:
      default:
        external:
          name: ocs-net
    services:
      influxdb:
        image: "influxdb:1.7"
        container_name: "influxdb"
        restart: always
        ports:
          - "8086:8086"
        environment:
          - INFLUXDB_HTTP_LOG_ENABLED=false
        volumes:
          - /srv/influxdb:/var/lib/influxdb

::

    # crossbar/docker-compose.yml
    version: '3.7'
    networks:
      default:
        external:
          name: ocs-net
    services:
      crossbar:
        image: simonsobs/ocs-crossbar:latest
        restart: always
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        environment:
          - PYTHONUNBUFFERED=1

::

    # web/docker-compose.yml
    version: '3.7'
    networks:
      default:
        external:
          name: ocs-net
    volumes:
      grafana-storage:
    services:
      grafana:
        image: grafana/grafana:latest
        restart: always
        ports:
          - "127.0.0.1:3000:3000"
        volumes:
          - grafana-storage:/var/lib/grafana

::

    # docker-compose.yml
    version: '3.7'
    networks:
      default:
        external:
          name: ocs-net
    services:
      ocs-aggregator:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        user: "9000"
        environment:
          - INSTANCE_ID=aggregator
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro
          - "/data:/data"
        depends_on:
          - "crossbar"

      ocs-influx-publisher:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        environment:
          - INSTANCE_ID=influxagent
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro

      ocs-LSA99ZZ:
        image: simonsobs/ocs-lakeshore372-agent:latest
        hostname: grumpy-docker
        network_mode: "host"
        environment:
          - INSTANCE_ID=LSA99ZZ
          - SITE_HUB=ws://10.10.10.2:8001/ws
          - SITE_HTTP=http://10.10.10.2:8001/call
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro

Once the separate influxdb, crossbar, and web services are brought up, they
should rarely need to be restarted, and are configured to automatically start
at boot. This allows one to restart or shutdown the OCS Agents completely
separately without worry of bringing down other components of the system.

.. note::
    This uses a Docker network, "ocs-net", which needs to be configured.
    Details can be found in :ref:`multiconfig`.
