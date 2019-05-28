.. highlight:: rst

Running Docker
==============

Alright, we've installed everything, configured everything, moment of truth.
Now we run the Docker containers. Until things are hosted publicly we need to
login to the private Docker registry hosted at Yale. (The password can be found
on the `SO wiki
<http://simonsobservatory.wikidot.com/tech:daq:credentials>`_.) To do so run::

    $ sudo docker login grumpy.physics.yale.edu
    Username: simonsobs
    Password: 

You will see output along the lines of::

    WARNING! Your password will be stored unencrypted in /home/koopman/.docker/config.json.
    Configure a credential helper to remove this warning. See
    https://docs.docker.com/engine/reference/commandline/login/#credentials-store
    
    Login Succeeded

Now we're ready to run Docker. From your institution configuration directory
(where the ``docker-compose.yml`` file is), run::

    $ docker-compose up -d

.. note::
    The ``-d`` flag daemonizes the containers. If you remove it the output from
    every container will be attached to your terminal. This can be useful for
    debugging.

You can confirm the running state of the containers with the ``docker ps``
command::

    $ bjk49@grumpy:~$ sudo docker ps
    CONTAINER ID        IMAGE                                                COMMAND                  CREATED             STATUS              PORTS                      NAMES
    4ab60968e656        grumpy.physics.yale.edu/dans-example-sensors:0.1.0   "python3 -u server_e…"   17 hours ago        Up 17 hours                                    yale_sensors_1_ed32e440a51c
    897cc97db4de        grumpy.physics.yale.edu/dans-ucsc-radiometer:0.1.0   "python3 -u radiomet…"   17 hours ago        Up 17 hours                                    yale_ucsc-radiometer_1_d7e361d12762
    1e388028651e        grumpy.physics.yale.edu/dans-thermometry:0.1.0       "python3 thermometry…"   17 hours ago        Up 17 hours                                    yale_LSA23JD_1_95c3e0153827
    41ee1f3a5407        grumpy.physics.yale.edu/dans-example-weather:0.1.0   "python3 -u server_e…"   17 hours ago        Up 17 hours                                    yale_weather_1_3653fc00295b
    51e472443467        grumpy.physics.yale.edu/dans-apex-weather:0.1.0      "python3 -u apex_wea…"   17 hours ago        Up 17 hours                                    yale_apex-weather_1_7de5c584d50e
    c078d7381bf9        grumpy.physics.yale.edu/sisock-http:0.1.0            "python3 -u grafana_…"   17 hours ago        Up 17 hours                                    yale_sisock-http_1_4e3ac7edff53
    de99780d0cfc        grafana/grafana:5.4.0                                "/run.sh"                17 hours ago        Up 17 hours         127.0.0.1:3000->3000/tcp   yale_grafana_1_93ec3ee6812b
    b3e049222a54        grumpy.physics.yale.edu/sisock-crossbar:0.1.0        "crossbar start"         17 hours ago        Up 17 hours         127.0.0.1:8001->8001/tcp   sisock_crossbar

This example shows all the containers running at Yale at the time of this
writing.
