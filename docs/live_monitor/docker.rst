.. highlight:: rst

Running Docker
==============

Our dependencies are met, the environment setup, and the configuration files
configured; Now we're ready to run Docker. From your institution configuration
directory (where the ``docker-compose.yml`` file is), run::

    $ docker-compose up -d

.. note::
    The ``-d`` flag daemonizes the containers. If you remove it the output from
    every container will be attached to your terminal. This can be useful for
    debugging.

You can confirm the running state of the containers with the ``docker ps``
command::

    $ bjk49@grumpy:~$ sudo docker ps
    CONTAINER ID        IMAGE                                                                COMMAND                  CREATED             STATUS              PORTS                      NAMES
    f325b0a95384        grumpy.physics.yale.edu/ocs-lakeshore240-agent:latest                "python3 -u LS240_ag…"   47 hours ago        Up 47 hours                                    prod_ocs-LSA22ZC_1_2cc23a32f274
    e27946e2806f        grumpy.physics.yale.edu/ocs-lakeshore240-agent:latest                "python3 -u LS240_ag…"   47 hours ago        Up 47 hours                                    prod_ocs-LSA22Z2_1_e8ae8bdfcbe1
    123c43ade64c        grumpy.physics.yale.edu/ocs-lakeshore240-agent:latest                "python3 -u LS240_ag…"   47 hours ago        Up 47 hours                                    prod_ocs-LSA24R5_1_81cb5b556c75
    d0484abc5e22        grumpy.physics.yale.edu/ocs-lakeshore372-agent:latest                "python3 -u LS372_ag…"   2 days ago          Up 2 days                                      prod_ocs-LSA22YE_1_345860de361e
    fb1274ec0983        grumpy.physics.yale.edu/ocs-lakeshore372-agent:latest                "python3 -u LS372_ag…"   2 days ago          Up 2 days                                      prod_ocs-LSA22YG_1_eccac22afb71
    c4994af324f7        grumpy.physics.yale.edu/sisock-weather-server:v0.2.11                "python3 -u server_e…"   2 days ago          Up 2 days                                      prod_weather_1_b7f76f317d75
    fed155bfcfad        grumpy.physics.yale.edu/sisock-g3-reader-server:v0.2.11-1-g1ff12ac   "python3 -u g3_reade…"   2 days ago          Up 2 days                                      prod_g3-reader_1_9e7e53ec96b0
    70288c5d6ce6        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA22YG_1_cd64f9656cfe
    dd4906561ed1        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA23JD_1_9a57b3fa29df
    5956786cd5b4        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA22YE_1_b5f1673d913f
    810258e8893c        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA22Z2_1_e6316efdbb2d
    d8db9af9a1de        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA24R5_1_19e6469ef97b
    91ecab00bd26        grumpy.physics.yale.edu/sisock-thermometry-server:v0.2.11            "python3 -u thermome…"   2 days ago          Up 2 days                                      prod_LSA22ZC_1_e1436bd60b9b
    d92bcdf8468a        grumpy.physics.yale.edu/sisock-http:v0.2.11                          "python3 -u grafana_…"   2 days ago          Up 2 days                                      prod_sisock-http_1_aeeb14fced5e
    2a782c1aa9c4        eee74fd50cf5                                                         "python3 -u registry…"   2 days ago          Up 2 days                                      prod_ocs-registry_1_ecacce7345b6
    7e8e3d7372ca        grumpy.physics.yale.edu/ocs-aggregator-agent:latest                  "python3 -u aggregat…"   2 days ago          Up 47 hours                                    prod_ocs-aggregator_1_5ed8fe90f913
    8e7129ab199d        grumpy.physics.yale.edu/sisock-crossbar:v0.2.11                      "crossbar start"         2 days ago          Up 2 days           127.0.0.1:8001->8001/tcp   prod_sisock-crossbar_1_7b0eb9ec21ff
    a98066cc4569        grumpy.physics.yale.edu/sisock-g3-file-scanner:v0.2.11-1-g1ff12ac    "python3 -u scan.py"     6 days ago          Up 6 days                                      prod_g3-file-scanner_1_99d392723812
    ddd6f1a63821        grafana/grafana:5.4.0                                                "/run.sh"                6 days ago          Up 6 days           127.0.0.1:3000->3000/tcp   prod_grafana_1_817207e03f75
    cc0ef28deef0        e07bb20373d8                                                         "docker-entrypoint.s…"   6 days ago          Up 6 days           3306/tcp                   prod_database_1_a7c15d7039b9

This example shows all the containers running at Yale at the time of this
writing.

.. note::

    Since all the OCS Agents are configured to run in containers (which is our
    recommendation for running your system), there is no additional startup of OCS
    Agents. Previously these were either started individually by calling the agent
    script in a terminal, or using the `ocsbow` tool.

    If your system is still setup to use these methods you can move to the
    Docker configuration by adding the required Agents to your docker-compose
    configuration and moving the Agent configurations in the ocs config file to a
    docker host block.

Using Docker
------------
Many users may not be familiar with using Docker. Here are some useful tips for
interacting with docker.

Viewing Logs
````````````
Each container has its own logs to which the output from the program running
inside the container is written. The logs can be viewed with::

    $ sudo docker logs <container name>

If you want to follow the logs (much like you would ``tail -f`` a file) you can run::

    $ sudo docker logs -f <container name>

Updating Containers
```````````````````
If you have made changes to the docker compose configuration you can update
your containers by running ``docker-compose up`` again. This will rebuild any
containers that have been updated. You can also restart individual containers
with::

    $ sudo docker-compose restart <container name>

Shutting Down All Containers
````````````````````````````
All the containers started with Compose can be stopped with::

    $ sudo docker-compose down
