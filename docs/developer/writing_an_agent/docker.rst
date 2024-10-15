Dockerizing an Agent
--------------------

Now that our Agent is complete, and we know it runs natively we want to deploy
it. A common way to do this is using Docker. Depending on the context for your
development this process might look different.

#. If you are adding an Agent to an existing OCS plugin you might be able to
   use the Docker image provided by that plugin (assuming it provides one.)
   This is simple if your Agent does not require any additional dependencies.
#. If you are adding an Agent to an existing OCS plugin, but it lacks the
   dependencies required to run your Agent you should consider adding those
   dependencies to that plugin's Docker image.
   See :ref:`dockerizing_agent_or_plugin` for information on how to write (or
   modify) a Dockerfile for a plugin.
#. If you are adding an Agent to an existing OCS plugin, but the dependencies
   are complicated or you need a different entrypoint you should create a separate
   Docker image for you Agent. This can be based on the plugin's base image.
   See :ref:`dockerizing_agent_or_plugin` for information on how to write (or
   modify) a Dockerfile for an Agent.
#. If you are creating an Agent outside of an existing OCS plugin you will
   build an image based on the OCS base image. We will describe this on this
   page below.

Here we assume the Agent is not apart of a package or OCS plugin. Start by
creating a file called ``Dockerfile`` in your Agent's directory:

.. code-block:: dockerfile

    # OCS Barebones Agent
    # ocs Agent for demonstrating how to write an Agent

    # Use ocs base image
    FROM simonsobs/ocs:latest

    # Set the working directory to copy your Agent into
    WORKDIR /app/agents/barebones_agent/

    # If there are extra dependencies install them here

    # Copy the current directory into the WORKDIR
    COPY . .

    # Run registry on container startup
    ENTRYPOINT ["dumb-init", "ocs-agent-cli"]

    # Set default commandline arguments
    CMD ["--agent", "barebones_agent.py", "--entrypoint", "main"]

Then from the Agent directory:

.. code-block:: bash

    $ docker build -t ocs-barebones-agent .
    Sending build context to Docker daemon   2.56kB
    Step 1/5 : FROM simonsobs/ocs:latest
     ---> ffe70796b093
    Step 2/5 : WORKDIR /app/agents/barebones_agent/
     ---> Running in 123cd75bd3df
    Removing intermediate container 123cd75bd3df
     ---> 9dbcef5d0a88
    Step 3/5 : COPY . .
     ---> d632fe89c0ab
    Step 4/5 : ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
     ---> Running in 0aab84608b57
    Removing intermediate container 0aab84608b57
     ---> bf8aba93e055
    Step 5/5 : CMD ["--agent", "barebones_agent.py", "--entrypoint", "main"]
     ---> Running in e4cefc3c6458
    Removing intermediate container e4cefc3c6458
     ---> 185f74d5f6c4
    Successfully built 185f74d5f6c4
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

We also need to add a configuration block to our docker compose file:

.. code-block:: yaml

    ocs-barebones-agent:
      image: ocs-barebones-agent
      hostname: ocs-docker
      volumes:
        - ./:/config:ro
      environment:
        - INSTANCE_ID=barebones1
        - LOGLEVEL=info

The "image" line corresponds to your newly built Docker image. The "hostname"
changes the hostname of the system within the container to the given argument.
This must match the hostname you configured the Agent under in your SCF. By
convention in OCS this is the name of your main system with an added "-docker".
"volumes" contains one or more mounted directories, in this case mounting the
current directory (``./``) outside of the container to ``/config`` within the
container, and do so read-only. Lastly, "environment" sets environment
variables within the container, in this case the instance-id and log level.

Now we can run the Agent with ``docker compose``:

.. code-block:: bash

    $ docker compose up -d

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

Building Images Automatically
-----------------------------

.. note::

    This section is applicable to the core ocs repo. It may or may not apply
    for other OCS plugins, depending on their build process.

In context 3 we want to add a new separate Docker image for our Agent. In
order for our Docker image to be built automatically by the continuous
integration pipeline we must also add some configuration to the main
``docker-compose.yaml`` file at the root of the repository:

.. code-block::

    ocs-barebones-agent:
      image: "ocs-barebones-agent"
      build: ./docker/barebones_agent/
      depends_on:
        - "ocs"

Here the "build" path points to the directory containing the ``Dockerfile`` for
our Agent.
