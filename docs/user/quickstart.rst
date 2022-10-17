.. _quickstart:

Quickstart
==========

We will assume you have already gone through the :ref:`ocs_install` part of the
documentation and thus have installed the required dependencies, namely Docker,
Docker Compose, and ocs.

In this example we will run an OCS Agent (the Fake Data Agent) which generates
random data, pass the data to an InfluxDB, and view the data in Grafana.

Configuration Files
-------------------
Before we begin we need to setup the configuration files. Let's first create a
directory to keep all of our site configuration files in::

    $ mkdir -p ocs-site-configs
    $ cd ocs-site-configs/

OCS needs to know where these configuration files are stored, and does so
through the ``OCS_CONFIG_DIR`` environment variable. In the terminal you are
using run::

    $ export OCS_CONFIG_DIR=$(pwd)

You can also set this more permanently in your ``.bashrc`` file. More details
in :ref:`environment_setup`.

.. note::

    This quickstart example includes only a couple Agents. The Agent Reference
    pages, linked in the sidebar, contain example configuration blocks for
    configuring each Agent.

Next, we need to write our two configuration files, starting with the OCS site
config file. You must replace "<hostname>" in this file with the hostname of
the computer you are working on. Also replace "<user>" with your username, or
change the paths "<user>" is in entirely to reflect your desired file
structure.

**default.yaml**::

    # Site configuration for a fake observatory.
    hub:
    
      wamp_server: ws://localhost:8001/ws
      wamp_http: http://localhost:8001/call
      wamp_realm: test_realm
      address_root: observatory
      registry_address: observatory.registry
    
    hosts:
    
      <hostname>: {
        # Directory for logs.
        'log-dir': '/home/<user>/log/ocs/',

        # List of additional paths to Agent plugin modules.
        'agent-paths': [
            '/home/<user>/git/ocs/agents/',
            '/home/<user>/git/socs/agents/',
        ],

        # Agents running directly on the host machine
        # Note: We aren't going to run this Agent in the quickstart example,
        #       but this gives a good example of configuring an agent directly
        #       on the host
        'agent-instances': [
          {'agent-class': 'HostManager',
           'instance-id': 'hm-1',
           'arguments': ['--initial-state', 'up']},
        ]   
      }
    
      <hostname>-docker: {
        # Address of crossbar within Docker (based on service name)
        'wamp_server': 'ws://crossbar:8001/ws',
        'wamp_http': 'http://crossbar:8001/call',
    
        # Agents running within Docker containers
        'agent-instances': [
          {'agent-class': 'InfluxDBAgent',
           'instance-id': 'influxagent',
           'arguments': ['--initial-state', 'record']},
          {'agent-class': 'FakeDataAgent',
           'instance-id': 'fake-data1',
           'arguments': ['--mode', 'acq',
                         '--num-channels', '16',
                         '--sample-rate', '4']},
        ]   
      }

Next, we need to define the Docker Compose file. Again, "<hostname>" should be
replaced with the hostname of your computer.

**docker-compose.yaml**::

    version: '3.7' 
    volumes:
      grafana-storage:
      influxdb-storage:

    services:
      # --------------------------------------------------------------------------
      # Grafana for the live monitor.
      # --------------------------------------------------------------------------
      grafana:
        image: grafana/grafana:latest
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
        volumes:
          - influxdb-storage:/var/lib/influxdb
    
      # --------------------------------------------------------------------------
      # Crossbar Server
      # --------------------------------------------------------------------------
      crossbar:
        image: simonsobs/ocs-crossbar:latest
        ports:
          - "127.0.0.1:8001:8001" # expose for OCS
        environment:
             - PYTHONUNBUFFERED=1
    
      # --------------------------------------------------------------------------
      # OCS Components
      # --------------------------------------------------------------------------
      # Fake Data Agent for example housekeeping data 
      ocs-fake-data1:
        image: simonsobs/ocs:latest
        hostname: <hostname>-docker
        environment:
          - INSTANCE_ID=fake-data1
          - LOGLEVEL=info
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro

      # InfluxDB Publisher 
      ocs-influx-publisher:
        image: simonsobs/ocs:latest
        hostname: <hostname>-docker
        environment:
          - INSTANCE_ID=influxagent
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro
    
Running
-------

Now that the system is configured, we can start it with a single
``docker-compose`` command::

    $ sudo -E docker-compose up -d
    Creating network "ocs-site-configs_default" with the default driver
    Creating ocs-site-configs_ocs-influx-publisher_1 ... done
    Creating ocs-site-configs_grafana_1              ... done
    Creating ocs-site-configs_ocs-fake-data1_1       ... done
    Creating ocs-site-configs_crossbar_1             ... done
    Creating influxdb                                ... done

.. note::
    If this is the first time you have run the example, you will see Docker
    Compose "pulling" (downloading) all the required images from DockerHub.

.. note::
    The ``-E`` here preserves the user environment within sudo, so
    ``$OCS_CONFIG_DIR`` still resolves properly.

You can view the running containers with::

    $ sudo docker ps
    CONTAINER ID   IMAGE                                           COMMAND                  CREATED          STATUS          PORTS                                          NAMES
    dc3792e8d4f3   influxdb:1.7                                    "/entrypoint.sh infl…"   27 seconds ago   Up 25 seconds   0.0.0.0:8086->8086/tcp, :::8086->8086/tcp      influxdb
    7aa0c07345de   simonsobs/ocs-crossbar:latest                   "crossbar start --cb…"   27 seconds ago   Up 25 seconds   8000/tcp, 8080/tcp, 127.0.0.1:8001->8001/tcp   ocs-site-configs_crossbar_1
    88dd47cc6714   simonsobs/ocs:latest                            "dumb-init python3 -…"   27 seconds ago   Up 25 seconds                                                  ocs-site-configs_ocs-fake-data1_1
    41231a482dec   simonsobs/ocs:latest                            "dumb-init python3 -…"   27 seconds ago   Up 25 seconds                                                  ocs-site-configs_ocs-influx-publisher_1
    bcdc0423ab4c   grafana/grafana:latest                          "/run.sh"                27 seconds ago   Up 25 seconds   127.0.0.1:3000->3000/tcp                       ocs-site-configs_grafana_1

If anything has gone wrong and some containers have not started, you can view
all containers, even stopped ones with::

    $ sudo docker container ls -a

Commanding
----------
The Agents can now be commanded using an OCS Client. To do so, we will open a Python interpreter and run::

    $ python
    >>> from ocs.ocs_client import OCSClient
    >>> client = OCSClient('fake-data1')
    >>> client.delay_task.start(delay=10)

For more details on how to use OCSClient and how to write a control program see
the Developer Guide section on :ref:`clients`.

Viewing
-------
Now that all of the containers are running 
we can view the random data being automatically generated by the
Fake Data Agent in Grafana. You can access Grafana by pointing your web
browswer to `<http://localhost:3000/>`_. For information about how to configure
the InfluxDB data source please see :ref:`influxdb_publisher`. Following that
page you should be able to view a live datastream from the Fake Data Agent.

.. note::
    The default Grafana credentials are "admin"/"admin".

Next Steps
----------
From here the possibilities are endless. You can add additional Agents for more
hardware, viewing their datastreams in Grafana, write a :ref:`Client
<clients>` to interact with the running Agents, or develop your own :ref:`Agent
<agents>` to control any unsupported hardware.

Shutdown
--------
If you'd just like to shutdown the example you can run::

    $ sudo docker-compose down

This will shutdown and remove all the containers.

If you would also like to remove any Docker images you may have downloaded you
can identify them with::

    $ sudo docker image ls

And remove them with::

    $ sudo docker image rm <image name>

.. warning::
    Running the following command will cause data within the containers to be
    lost! This includes Grafana dashboard configurations and data within
    InfluxDB.

If you would like to totally remove all trace of your OCS instance, including
the storage volumes, run::

    $ sudo docker-compose down --volumes
