Dockerizing an Agent
--------------------

Now that our Agent is complete, and we know it runs natively, let's build it
into a Docker container. If your Agent has any complicated dependencies this
will help with deployment on user's machines. Start by creating a file called
``Dockerfile`` in your Agent's directory:

.. code-block:: dockerfile

    # OCS Barebones Agent
    # ocs Agent for demonstrating how to write an Agent
    
    # Use ocs base image
    FROM ocs:latest
    
    # Set the working directory to registry directory
    WORKDIR /app/ocs/agents/barebones_agent/
    
    # Copy this agent into the WORKDIR
    COPY . .
    
    # Run registry on container startup
    ENTRYPOINT ["dumb-init", "python3", "-u", "barebones_agent.py"]
    
    # Sensible defaults for crossbar server
    CMD ["--site-hub=ws://crossbar:8001/ws", \
         "--site-http=http://crossbar:8001/call"]

At this point you should have a directory structure that looks somewhat like this:

.. code-block:: bash

    ├── ocs
    │   ├── agents
    │   │   ├── aggregator
    │   │   ├── barebones_agent
    │   │   │   ├── barebones_agent.py
    │   │   │   └── Dockerfile
    │   │   ├── fake_data
    │   │   ├── host_manager
    │   │   ├── influxdb_publisher
    │   │   ├── ocs_plugin_standard.py
    │   │   └── registry
    │   ├── bin
    │   ├── CONTRIBUTING.rst
    │   ├── docker
    │   ├── docker-compose.yml
    │   ├── Dockerfile
    │   ├── docs
    │   ├── example
    │   ├── LICENSE.txt
    │   ├── Makefile
    │   ├── MANIFEST.in
    │   ├── ocs
    │   ├── pyproject.toml
    │   ├── README.rst
    │   ├── requirements
    │   ├── requirements.txt
    │   ├── setup.cfg
    │   ├── setup.py
    │   ├── tests
    │   ├── versioneer.py
    └── ocs-site-configs
        ├── default.yaml
        └── docker-compose.yaml

We can now build the Docker image for the Agent. First we need to make sure the
ocs base container is built. From the root of the ocs repository run:

.. code-block:: bash

    $ docker build -t ocs .

Then from the Agent directory:

.. code-block:: bash

    $ docker build -t ocs-barebones-agent .
    Sending build context to Docker daemon  68.61kB
    Step 1/5 : FROM ocs:latest
     ---> bb938fc7d43b
    Step 2/5 : WORKDIR /app/ocs/agents/barebones_agent/
     ---> Running in 5167620dc9aa
    Removing intermediate container 5167620dc9aa
     ---> 9ee12c04df26
    Step 3/5 : COPY . .
     ---> 81c1c08b9f32
    Step 4/5 : ENTRYPOINT ["dumb-init", "python3", "-u", "barebones_agent.py"]
     ---> Running in 67e56599a784
    Removing intermediate container 67e56599a784
     ---> b4c651ce8546
    Step 5/5 : CMD ["--site-hub=ws://crossbar:8001/ws",      "--site-http=http://crossbar:8001/call"]
     ---> Running in f58cd0c3e762
    Removing intermediate container f58cd0c3e762
     ---> fdef661823cb
    Successfully built fdef661823cb
    Successfully tagged ocs-barebones-agent:latest

Now we can use the Dockerized version of our Agent by modifying our SCF, moving
the BarbonesAgent config to the ``ocs-docker`` host.:

.. code-block:: yaml

    # Site configuration for a fake observatory.
    hub:
    
      wamp_server: ws://localhost:8001/ws
      wamp_http: http://localhost:8001/call
      wamp_realm: test_realm
      address_root: observatory
      registry_address: observatory.registry
    
    hosts:
    
      ocs-docker: {
        'wamp_server': 'ws://crossbar:8001/ws',
        'wamp_http': 'http://crossbar:8001/call',
    
        'agent-instances': [
          {'agent-class': 'BarebonesAgent',
           'instance-id': 'barebones1',
           'arguments': ['--mode', 'idle']},
        ]
      }

We also need to add a configuration block to our docker-compose file:

.. code-block:: yaml

    ocs-barebones-agent:
      image: ocs-barebones-agent
      hostname: ocs-docker
      volumes:
        - ./:/config:ro
      environment:
        - LOGLEVEL=info

The "image" line corresponds to your newly built Docker image. The "hostname"
changes the hostname of the system within the container to the given argument.
This must match the hostname you configured the Agent under in your SCF. By
convention in OCS this is the name of your main system with an added "-docker".
"volumes" contains one or more mounted directories, in this case mounting the
current directory (``./``) outside of the container to ``/config`` within the
container, and do so read-only. Lastly, "environment" sets environment
variables within the container, in this case the log level.

Now we can run the Agent with ``docker-compose``:

.. code-block:: bash

    $ docker-compose up -d

Once the containers have started, you can see the running containers with:

.. code-block:: bash

    $ docker ps
    CONTAINER ID   IMAGE                                 COMMAND                  CREATED         STATUS         PORTS                                                           NAMES
    80cc47c7b476   ocs:latest                            "bash"                   4 seconds ago   Up 1 second                                                                    barebones-agent-dev-ocs-client-1
    e4dac1f43450   ocs-barebones-agent                   "dumb-init python3 -…"   4 seconds ago   Up 2 seconds                                                                   barebones-agent-dev-ocs-barebones-agent-1
    c7e124c543e6   grafana/grafana:7.1.0                 "/run.sh"                4 seconds ago   Up 2 seconds   127.0.0.1:3000->3000/tcp                                        barebones-agent-dev-grafana-1
    ed64b4aca954   ocs-fake-data-agent:latest            "dumb-init python3 -…"   4 seconds ago   Up 2 seconds                                                                   barebones-agent-dev-fake-data1-1
    1d37cf0d8d22   ocs-influxdb-publisher-agent:latest   "dumb-init python3 -…"   4 seconds ago   Up 2 seconds                                                                   barebones-agent-dev-ocs-influx-publisher-1
    4f0a8fa762f5   ocs-web:latest                        "docker-entrypoint.s…"   4 seconds ago   Up 2 seconds   8080/tcp, 127.0.0.1:3002->80/tcp                                barebones-agent-dev-ocs-web-1
    b5ce20809c73   simonsobs/ocs-crossbar:v0.8.0         "crossbar start --cb…"   4 seconds ago   Up 2 seconds   8000/tcp, 8080/tcp, 0.0.0.0:8001->8001/tcp, :::8001->8001/tcp   barebones-agent-dev-crossbar-1
    1bd06acf8da6   ocs-registry-agent:latest             "dumb-init python3 -…"   4 seconds ago   Up 2 seconds                                                                   ocs-registry
    6f785c871bc7   influxdb:1.7                          "/entrypoint.sh infl…"   4 seconds ago   Up 2 seconds   0.0.0.0:8086->8086/tcp, :::8086->8086/tcp                       influxdb

The Agent's logs should be available (using the container name from the
``docker ps`` output):

.. code-block:: bash

    $ docker logs -f barebones-agent-dev-ocs-barebones-agent-1
    2022-07-25T19:38:44+0000 Using OCS version 0.9.3
    2022-07-25T19:38:44+0000 ocs: starting <class 'ocs.ocs_agent.OCSAgent'> @ observatory.barebones1
    2022-07-25T19:38:44+0000 log_file is apparently None
    2022-07-25T19:38:44+0000 transport connected
    2022-07-25T19:38:44+0000 session joined: {'authextra': {'x_cb_node': '77345e0dc974-1',
                   'x_cb_peer': 'tcp4:192.168.32.10:55534',
                   'x_cb_pid': 17,
                   'x_cb_worker': 'worker001'},
     'authid': '95Y5-U69J-5HRE-9TWL-9JYR-6UFH',
     'authmethod': 'anonymous',
     'authprovider': 'static',
     'authrole': 'iocs_agent',
     'realm': 'test_realm',
     'resumable': False,
     'resume_token': None,
     'resumed': False,
     'serializer': 'msgpack.batched',
     'session': 3435966848712686,
     'transport': {'channel_framing': 'websocket',
                   'channel_id': {},
                   'channel_serializer': None,
                   'channel_type': 'tcp',
                   'http_cbtid': None,
                   'http_headers_received': None,
                   'http_headers_sent': None,
                   'is_secure': False,
                   'is_server': False,
                   'own': None,
                   'own_fd': -1,
                   'own_pid': 7,
                   'own_tid': 7,
                   'peer': 'tcp4:192.168.32.7:8001',
                   'peer_cert': None,
                   'websocket_extensions_in_use': None,
                   'websocket_protocol': None}}

We can still use a Client as we had before:

.. code-block::

    >>> from ocs.ocs_client import OCSClient
    >>> client = OCSClient('barebones1')
    >>> client.count.start()
    OCSReply: OK : Started process "count".
      count[session=0]; status=starting for 0.008071 s
      messages (1 of 1):
        1658783149.174 Status is now "starting".
      other keys in .session: op_code, data
    >>> client.count.status()
    OCSReply: OK : Session active.
      count[session=0]; status=running for 7.0 s
      messages (2 of 2):
        1658783149.174 Status is now "starting".
        1658783149.177 Status is now "running".
      other keys in .session: op_code, data
    >>> client.count.status().session['data']
    {'value': 14, 'timestamp': 1658783162.1936133}
    >>> client.count.stop()
    OCSReply: OK : Requested stop on process "count".
      count[session=0]; status=running for 17.4 s
      messages (2 of 2):
        1658783149.174 Status is now "starting".
        1658783149.177 Status is now "running".
      other keys in .session: op_code, data

In the docker logs you will see:

.. code-block::

    2022-07-25T21:05:49+0000 start called for count
    2022-07-25T21:05:49+0000 count:0 Status is now "starting".
    2022-07-25T21:05:49+0000 Starting the count!
    2022-07-25T21:05:49+0000 count:0 Status is now "running".
    2022-07-25T21:06:07+0000 count:0 Acquisition exited cleanly.
    2022-07-25T21:06:07+0000 count:0 Status is now "done".

In order for our Docker image to be built automatically by the continuous
integration pipeline we must also add some configuration to the main
``docker-compose.yaml`` file at the root of the repository:

.. code-block::

    ocs-barebones-agent:
      image: "ocs-barebones-agent"
      build: ./agents/barebones_agent/
      depends_on:
        - "ocs"
