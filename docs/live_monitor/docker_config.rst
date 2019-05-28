.. highlight:: rst

sisock
------

The sisock_ repo provides the infrastructure we'll need to perform live
monitoring. The code provided all runs within Docker containers. To configure
which containers will be run we edit the ``docker-compose.yml`` file.

Setup the Docker Environment
````````````````````````````

If this is your first time using Docker to run sisock then we need to do some
first time setup. In the site-config ``templates/`` directory (and thus in your
copy of it for your institution) there should be a script called
``init-docker-env.sh``. Running this does two things, creates a separate Docker
bridge network for the sisock stack to communicate over, and creates a storage
volume for Grafana so that any configuration we do survives when we shutdown
the container. To setup the Docker environment run the script::

    $ sudo ./init-docker-env.sh

Configure ``docker-compose.yaml``
`````````````````````````````````

The site-config repo ships a template ``docker-compose.yml`` file which has an
example configuration for each available sisock container. We just need to
choose the ones we need for our application. Details about each container can
be found in the `sisock documentation`_

.. _`sisock documentation`: https://grumpy.physics.yale.edu/docs/sisock/

The template ``docker-compose.yml`` file, looks something like this (Note: I've
excluded some examples that you probably won't need)::

    version: '2' 
    networks:
      default:
        external:
          name: sisock-net
    volumes:
      grafana-storage:
        external: true
    services:
      grafana:
        image: grafana/grafana:5.4.0
        restart: always
        ports:
          - "127.0.0.1:3000:3000"
        environment:
          - GF_INSTALL_PLUGINS=grafana-simple-json-datasource, natel-plotly-panel
        volumes:
          - grafana-storage:/var/lib/grafana
    
      sisock-crossbar:
        image: grumpy.physics.yale.edu/sisock-crossbar:0.1.0
        container_name: sisock_crossbar # required for proper name resolution in sisock code
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        volumes:
          - ./.crossbar:/app/.crossbar
        environment:
             - PYTHONUNBUFFERED=1
    
      sisock-http:
        image: grumpy.physics.yale.edu/sisock-http:0.1.0
        depends_on:
          - "sisock-crossbar"
        volumes:
          - ./.crossbar:/app/.crossbar:ro
    
      weather:
        image: grumpy.physics.yale.edu/dans-example-weather:0.1.0
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"
        volumes:
          - ./.crossbar:/app/.crossbar:ro
    
      LSA23JD:
        image: grumpy.physics.yale.edu/dans-thermometry:0.1.0
        environment:
            TARGET: LSA23JD # match to instance-id of agent to monitor, used for data feed subscription
            NAME: 'LSA23JD' # will appear in sisock a front of field name
            DESCRIPTION: "LS372 in the Bluefors control cabinet."
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"

The head of this file should remain untouched, it defines how our application
connects to the sisock-net and uses the ``grafana-storage`` volume that we
created using the ``init-docker-env.sh`` script.

Everything below ``services:`` defines a Docker container. Again, more details
on these containers is available in the `sisock documentation`_. Let's look at
each service individually, starting with the ``grafana`` service::

      grafana:
        image: grafana/grafana:5.4.0
        restart: always
        ports:
          - "127.0.0.1:3000:3000"
        environment:
          - GF_INSTALL_PLUGINS=grafana-simple-json-datasource, natel-plotly-panel
        volumes:
          - grafana-storage:/var/lib/grafana
    
This pulls the grafana image from Docker hub, configures it to startup at boot
(or in the event it crashes), exposes the port on which we can view the
interface on to the host computer, installs some helpful plugins, and tells the
container about the persistent storage. You can leave all these options as
configured in the template.

Next is the crossbar server, we have called in ``sisock-crossbar``. The image
is provided on a private Docker registry, hosted a Yale (we'll cover how to
access this before we run the containers. Soon this step will be removed and
the containers will be publicly hosted on Docker Hub.) 

We assign the container name ``sisock_crossbar``. Do not change this
container name, as it is coded within the sisock programs as the
domain name for use in accessing the crossbar server.  We expose the server to
the local host on port 8001 for communication with OCS. The sisock interface
with crossbar communicates over TLS and so we need to mount our TLS keys within
the container. Finally we make the output from python unbuffered, allowing easy
access to output in Docker's logs::

      sisock-crossbar:
        image: grumpy.physics.yale.edu/sisock-crossbar:0.1.0
        container_name: sisock_crossbar # required for proper name resolution in sisock code
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        volumes:
          - ./.crossbar:/app/.crossbar
        environment:
             - PYTHONUNBUFFERED=1
    
Next is the http server. This is the container which forms the glue layer
between sisock and grafana, allowing us to view live data. The name of this
container, ``sisock-http``, will become important once we are configuring the
grafana interface, as will the exposed port, 5000. You can keep all the
defaults here::

      sisock-http:
        image: grumpy.physics.yale.edu/sisock-http:0.1.0
        depends_on:
          - "sisock-crossbar"
        volumes:
          - ./.crossbar:/app/.crossbar:ro
    
The weather server is a demo sisock ``DataNodeServer`` which displays archived
APEX weather data. While you do not need this container, it is a helpful
debugging tool as it is very simple and should almost always work out of the
box::

      weather:
        image: grumpy.physics.yale.edu/dans-example-weather:0.1.0
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"
        volumes:
          - ./.crossbar:/app/.crossbar:ro
    
The remaining container is for a ``DataNodeServer`` which interfaces with
various thermometry readout components, either a Lakeshore 372 or a Lakeshore
240.::

      LSA23JD:
        image: grumpy.physics.yale.edu/dans-thermometry:0.1.0
        environment:
            TARGET: LSA23JD # match to instance-id of agent to monitor, used for data feed subscription
            NAME: 'LSA23JD' # will appear in sisock a front of field name
            DESCRIPTION: "LS372 in the Bluefors control cabinet."
        depends_on:
          - "sisock-crossbar"
          - "sisock-http"

The name we've given this container, ``LSA23JD``, corresponding to the serial
number of the Lakeshore 372.  You can change it to whatever you would like,
however, it must be unique among your containers. 

The ``environment`` sets up environment variables, which will be passed to the
container. These in turn are used in the thermometry ``DataNodeServer``. The
``TARGET`` variable must match the OCS ``instance-id`` of the agent we want to
monitor (already configured in your OCS ``institution.yaml`` file), as this is
used to select which data feed to subscribe to in OCS. The ``NAME`` variable
gives the ``DataNodeServer`` its name, which is used in constructing the fields
which will be shown in the Grafana interface for selection of the data when
plotting.

.. _sisock: https://github.com/simonsobs/sisock
