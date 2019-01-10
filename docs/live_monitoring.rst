.. highlight:: rst

.. _live_monitoring:

====================
OCS Live Monitoring
====================

OCS allows one to command and control their equipment, but how do we monitor
that equipment?

For that we use a combination of sisock_ and a web application called Grafana_.
This page describes setting up this entire tool chain.

.. contents::
    :backlinks: none

Dependencies
============

This is everything you will need to run the live monitor.

Hardware Requirements
---------------------

You will need a Linux computer running Ubuntu 18.04. Other
Operating Systems can be used, but will not be supported.

.. note::

    We'll be using Docker for a portion of this. This will pull images that
    containerize our applications, most of which are based on a base Python image.
    This will take disk space in your root filesystem. If you partition for a small
    / you might run into space constraints. In this case you should get in touch
    with Brian for advice on how best to proceed.

Software Requirements
---------------------

We'll need several pieces of software. To start:
    * Docker_ - Containerization software used for running sisock.
    * `Docker Compose`_ - Docker tool for running multi-container applications.
    * spt3g_ - For writing data to disk in ``.3g`` format.

SO software:
    * OCS_ - Our Observatory Control System.
    * sisock_ - For the live monitor. This will run in a Docker container, so
                we won't actually be installing it on our host system directly.

Networking Requirements
-----------------------

This Linux machine will need to go on the same network as whatever hardware
you're controlling with OCS. Live monitoring remotely (i.e. not sitting
directly at the computer) is facilitated if your IT department allows it to
have a public IP address.

.. warning::
    If you do have a public IP and traffic is allowed to
    all ports, you are strongly recommended to enable a firewall as described in
    firewall_. Care should also be taken when exposing ports in Docker to
    expose only to your localhost (i.e. 127.0.0.1), this is the default in all
    templates provided by the DAQ group.

.. note::
    If you do not have a public IP, but do have access to a gateway to
    your private network, then port forwarding can be used to view the live monitor
    remotely, as described in port_forwarding_.

.. _Installing OCS:

Software Installation
=====================

Installing Docker
-----------------

Docker is used to run many of the components related to sisock, including the
crossbar server, so we'll start by installing it on the computer we're running
everything on. To install, please follow the `Docker installation`_
documentation on their website.

.. note::

    The docker daemon requires root privileges. To avoid this you can add your user
    to the ``docker`` group. This is explained in the `post installation`_ steps,
    also in the Docker docs. However, we recommend you run as root through a
    sudo user.

When complete, the docker daemon should be running, you can check this by
running ``systemctl status docker`` and looking for output similar to the
following::

    $ systemctl status docker
    ● docker.service - Docker Application Container Engine
       Loaded: loaded (/lib/systemd/system/docker.service; disabled; vendor preset: enabled)
       Active: active (running) since Tue 2018-10-30 10:57:48 EDT; 2 days ago
         Docs: https://docs.docker.com
     Main PID: 1472 (dockerd)

If you see it is not active, run ``systemctl start docker``. To ensure it runs
after a computer reboot you should also run ``systemctl enable docker``.

Installing Docker Compose
-------------------------

Docker Compose facilitates running multi-container applications, which we have.
This will allow us to pull and run all the containers we need in a single
command. To install see the `Docker Compose`_ documentation.

When complete you should be able to run::

    $ docker-compose --version
    docker-compose version 1.22.0, build 1719ceb

.. note::

    The version shown here might not reflect the latest version available.

Installing spt3g
----------------

The spt3g_ library is provided by the SPT-3G collaboration and is publicly
available on Github.

.. todo::

    Add information for loading proper spt3g environment automatically.

Installing OCS
--------------

Install OCS with the following::

    $ git clone https://github.com/simonsobs/ocs.git
    $ cd ocs/
    $ pip3 install -r requirements.txt --user .

These directions are presented in the `OCS repo`_, which likely has the most up
to date version. If you need to update OCS, be sure to stash any changes you've
made before pulling updates from the repo.

.. _OCS site-config file:

Installing sisock
-----------------

sisock_ is not actually installed on the host system, all sisock components will
be pulled from a server automatically in the later steps.

Configuration
=============

We've now installed all the required software. Our next step is to properly
configure the OCS and sisock environments. To organize and version control each
institution/site's configuration we have made the ocs-site-config_ repository.
We will clone this repository and use the example templates as a starting point
for our new site::

    $ git clone https://github.com/simonsobs/ocs-site-configs.git

We'll first want to copy the templates directory and name it for our site (i.e.
``yale``)::

    $ cp -r templates/ yale/

Then we need to setup the TLS certificates for the crossbar server, to do this
a script called ``setup-tls.sh`` is provided, simply enter your new directory
and run it (swap ``yale`` for your institution)::

    $ cd yale/
    $ ./setup-tls.sh

This will generate the required certificates and put them in a directory called
``.crossbar/`` (which already existed in the copied template directory). Next
we need to configure both the OCS and sisock configuration files. These
configurations will differ based on the requirements at each institution.

OCS
---

Site configuration is described over on the page :ref:`site_config`. Here we will
look at the ``templates/ocs_template.yaml`` config as an example. (Note, you
should rename the template to be ``<your institution>.yaml``)::

    # Site configuration for a fake observatory.
    hub:
    
      wamp_server: ws://localhost:8001/ws
      wamp_realm: test_realm
      address_root: observatory
      registry_address: observatory.registry
    
    hosts:
    
      hostname: {
    
        # Description of a host's Agents.
    
        'agent-instances': [
          {'agent-class': 'Lakeshore372Agent',
           'instance-id': 'LSA22YE',
           'arguments': [['--serial-number', 'LSA22YE'],
                         ['--ip-address', '10.10.10.4']]},
          {'agent-class': 'Lakeshore240Agent',
           'instance-id': 'ls240',
           'arguments': [['--serial-number', 'LSA22ZC']]},
          {'agent-class': 'AggregatorAgent',
           'instance-id': 'aggregator',
           'arguments': []},
          {'agent-class': 'RegistryAgent',
           'instance-id': 'registry',
           'arguments': []},
        ]
    }

All of the information in the ``hub:`` section should remain unchanged, unless
you know what you're doing.

Under ``hosts:`` you'll need to replace ``hostname`` with the name of your
computer. If you don't know your computer's name, open a terminal and type
``hostname``, enter whatever comes out.

Each item under a given host describes the OCS Agents which may be run. For
example we'll look at the first 372 Agent here::

          {'agent-class': 'Lakeshore372Agent',
           'instance-id': 'LSA22YE',
           'arguments': [['--serial-number', 'LSA22YE'],
                         ['--ip-address', '10.10.10.4']]},

The ``agent-class`` is given by the actual Agent we'll be running. This must
match the name defined in the Agent's code. The ``instance-id`` is a unique
name given to this agent instance. Here we use the Lakeshore 372 serial number.
This will need to be noted for later use in the live monitoring. Finally the
arguments are used to pass default arguments to the Agent at startup, which
contains the serial number again as well as the IP address of the 372.

In order for OCS to know where to find your configuration file we need to take
two more steps. First, add the following to your ``.bashrc`` file::

    export OCS_CONFIG_DIR='/path/to/ocs-site-configs/<your-institution-directory>/'

Next, symlink your configuration file to ``default.yaml``::

    $ ln -s yale.yaml default.yaml

If you're proceeding in the same terminal don't forget to source your
``.bashrc`` file.

For more information see the :ref:`site_config` page in this documentation.

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

Configuring Grafana
===================

Now we are ready to configure Grafana. The configuration is not challenging,
however dashboard configuration can be time consuming. The ``grafana-storage``
volume that we initialized will allow for persistent storage in the event the
container is rebuilt. Dashboards can also be backed up by exporting them to a
``.json`` file.

.. warning::
    This should be a one time setup, however, if you destroy the
    grafana-storage volume you will lose your configuration. We encourage you
    to export your favorite dashboards for backup.

Set a Password
--------------

When you first navigate to ``localhost:3000`` in your web browser you will see
the following page:

.. image:: img/live_monitoring/grafana_01.jpg

The default username/password are ``admin``/``admin``. Once you enter this it
will prompt you to set a new admin password. Select something secure if your
computer faces the internet. If it's local only you can keep the default,
however whenever you login it will prompt you to change the default.

Configuring the Data Source
---------------------------

After setting the password you will end up on this page:

.. image:: img/live_monitoring/grafana_02.jpg

Click on the highlighted "Add data source" icon. This is also accessible under
the gear in the side menu as "Data Sources". You should then see this:

.. image:: img/live_monitoring/grafana_03.jpg

Here we configure the source from which Grafana will get all our data, this is
going to be the ``sisock-http`` server we started up in Docker. You can
fill in what you want for a name, though I'd suggest "sisock". Make sure the
"Default" checkbox is checked, as this will be our default data source when
creating a new Dashboard. Type must be "SimpleJson" (we installed this as a
plugin when we started up the Docker container, this is not a default option
available in Grafana). And finally the URL must be ``http://sisock-http:5000``.
This is the name for the HTTP server we set in the ``docker-compose.yml`` file
as well as the port we assigned it. Now you should have something that looks
identical to this:

.. image:: img/live_monitoring/grafana_04.jpg

When you click "Save & Test" a green alert box should show up, saying "Data
source is working", like this:

.. image:: img/live_monitoring/grafana_05.jpg

If the Data Source is not working you will see an HTTP Error Bad Gateway in red:

.. image:: img/live_monitoring/grafana_06.jpg

If this occurs it could be several things.

* Check the URL is correct
* Make sure you select the SimpleJson data source Type
* Check the sisock-http container is running
* Check you have added the grafana container to the sisock-net

Configuring a Dashboard
-----------------------

Now that we have configured the Data Source we can create our first Dashboard.
If you press back on the previous screen you will end up on the Data Sources
menu. From any page you should have access to the sidebar on the left hand side
of your browser. You may need to move your mouse near the edge of the screen to
have it show up. Scroll over the top '+' sign and select "Create Dashboard", as
shown here:

.. image:: img/live_monitoring/grafana_07.jpg

You will then see a menu like this:

.. image:: img/live_monitoring/grafana_08.jpg

In this menu we are selecting what type of Panel to add to our Dashboard. We'll
add a Graph. When we first add the Graph it will be blank:

.. image:: img/live_monitoring/grafana_09.jpg

Click on the "Panel Title", and in the drop down menu, click "Edit". This will
expand the plot to the full width of the page and present a set of tabbed menus
below it.

.. image:: img/live_monitoring/grafana_10.jpg

We start on the "Metrics" tab. Here is where we add the fields we
wish to plot. The drop down menu that says "select metric" will contain fields
populated by the sisock ``DataNodeServers``. Select an item in this list, for
instructional purposes we'll select a sensors metric, which is from the demo
CPU temperature ``DataNodeServer``. Data should appear in the plot, assuming
you are also running the ``dans-example-sensors`` demo container (though a
similar test can be performed with the ``dans-example-weather`` demo
container.)

.. image:: img/live_monitoring/grafana_11.jpg

You can configure the time interval and update intervals by clicking on the
time in the upper right, it most likely by default says "Last 6 hours":

.. image:: img/live_monitoring/grafana_12.jpg

The thermometry ``DataNodeServers`` by default cache the last 60 minutes of
data. Loading older data from disk is currently a work in progress.

Running the OCS Agents and Clients
==================================

Now that the live monitor is configured we can setup our OCS Agents which
communicate with our hardware and save the data to disk. This will involve at
least three Agents. For our example we will run the RegistryAgent, the data
Aggregator, and an LS372 Agent. 

.. note::
    An Agent for managing the running and startup of all these Agents is
    currently in the works, though is not quite ready yet. When done it will
    eliminate the need to start these individually. Bear with us for now.

We'll run these from within the OCS repo we cloned earlier, so navigate there.
The Agents are located within the aptly named ``agents/`` directory.

First, the RegistryAgent. To start we can just run the ``registry.py`` file::

    $ python3 registry.py
    2019-01-10T11:42:46-0500 transport connected
    2019-01-10T11:42:46-0500 session joined: SessionDetails(realm=<test_realm>, session=6826665888645921, authid=<FNRP-LLQG-AGY3-KXJ4-PJKT-ESYA>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)
    2019-01-10T11:42:46-0500 start called for register_agent
    2019-01-10T11:42:46-0500 register_agent:0 Status is now "starting".
    2019-01-10T11:42:46-0500 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Status is now "done".

Next the Aggregator Agent::

    $ python3 aggregator_agent.py
    2018-11-01T18:17:19-0400 transport connected
    2018-11-01T18:17:19-0400 session joined: SessionDetails(realm=<test_realm>, session=3951407465670067, authid=<PEL3-C365-75XL-KQUX-A9HK-UXA7>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)

Finally, the LS372 Agent. Note we specify the ``instance-id`` as configured in
our YAML file::

    $ python3 LS372_agent.py --instance-id=LSA23JD
    site_config is setting values of "serial_number" to "LSA23JD".
    site_config is setting values of "ip_address" to "10.10.10.6".
    I am in charge of device with serial number: LSA23JD
    2019-01-10T11:52:06-0500 transport connected
    2019-01-10T11:52:06-0500 session joined: SessionDetails(realm=<test_realm>, session=122770728011642, authid=<AW34-LK5L-CQGA-N9RP-QTYE-VUMQ>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)

Now we are ready to run an OCS Client which commands the agents to begin data
aggregation and data acquisition for this we will run ``clients/therm_and_agg_ctrl.py``::

    $ python3 therm_and_agg_ctrl.py --target=LSA23JD
    2019-01-10T11:53:52-0500 transport connected
    2019-01-10T11:53:52-0500 session joined: SessionDetails(realm=<test_realm>, session=1042697241527250, authid=<GJJU-4YG3-3UCG-CSMJ-TQTW-PWSM>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)
    2019-01-10T11:53:52-0500 Entered control
    2019-01-10T11:53:52-0500 Registering tasks
    2019-01-10T11:53:52-0500 Starting Aggregator
    2019-01-10T11:53:52-0500 Starting Data Acquisition

Data should now be displaying the terminal you started the LS372 Agent in, and
file output should be occurring in the configured Data Aggregator directory,
which the Agent reports.

Viewing the Live Monitor
========================

Now we should start to see data in our live monitor.

.. note::
    If no data is showing up, you may have to select the metrics drop down menu
    again when first starting up.  This is a known bug. Selecting the metric drop
    down should get data showing again. This is likely only a problem after you
    have a configured panel and restart the ``DataNodeServer``.

Here are some examples of what fully configured panels may look like:

.. figure:: img/live_monitoring/grafana_13.jpg

    The diode calibration setup at Penn. Six diodes are readout on a single
    Lakeshore 240. The top plot shows the calibrated diode, reporting temperature
    in Kelvin. While the bottom plot shows the 5 uncalibrated diodes.

    The Top element is a SingleStat panel which shows the current temperature
    of the 4K plate via the calibrated diode.

.. figure:: img/live_monitoring/grafana_14.jpg

    A demo Lakeshore 372 readout at Yale. The Lakeshore switches over 15
    channels, reading each out for a few seconds before moving onto the next.

    Here the first eight channels are shown on the left plot, and the last
    seven shown on the right plot. There are 15 single stat panels below the
    plots showing the current values for each given channel.

Other Info
==========

Grafana
-------

Backing up Panels
``````````````````

Networking
----------

.. _firewall:

Configuring a Firewall
``````````````````````

.. note::
    This problem is solved in part by the explicit exposure of the crossbar
    server port to localhost in our ``docker-compose.yml`` file in the line
    ``ports: "127.0.0.1:3000:3000"``. This ensures port 3000 is only available
    to the localhost. If this is not done (i.e. "ports: 3000:3000") Docker will
    manipulate the iptables to make port 3000 available anywhere, so if your
    computer is publicly facing anyone online can (and will) try to connect.
    This will be evident in your crossbar container's logs.

    That said, the firewall setup is not totally necessary, though still is
    good practice, so I will leave this information here.

If you have convinced your university IT department to allow you to have a
Linux machine on the public network we should take some precautions to secure
the crossbar server, which currently for OCS does not have a secure
authentication mechanism, from the outside world. The simplest way of doing so
is by setting up a firewall.

Ubuntu should come with (or have easily installable) a simple front end for
iptables called ufw (Uncomplicated Firewall). This is disabled by default.
Before configuring you should consider any software running on the machine
which may require an open port. We will configure it to have ports 22 and 3000
open, for ssh and Grafana, respectively.

``ufw`` should be disabled by default::

    $ sudo ufw status
    Status: inactive

You can get a list of applications which ``ufw`` knows about with::

    $ sudo ufw app list
    Available applications:
      CUPS
      OpenSSH

We can then allow the ssh port with::

    $ sudo ufw allow OpenSSH
    Rules updated
    Rules updated (v6)

This opens port 22. And finally, we can allow Grafana's port 3000::

    $ sudo ufw allow 3000
    Rules updated
    Rules updated (v6)

Lastly we have to enable ``ufw``::

    $ sudo ufw enable
    Command may disrupt existing ssh connections. Proceed with operation (y|n)? y
    Firewall is active and enabled on system startup

You should then see that the firewall is active::

    $ sudo ufw status
    Status: active

    To                         Action      From
    --                         ------      ----
    OpenSSH                    ALLOW       Anywhere
    3000                       ALLOW       Anywhere
    OpenSSH (v6)               ALLOW       Anywhere (v6)
    3000 (v6)                  ALLOW       Anywhere (v6)

.. _port_forwarding:

Port Forwarding to View Remotely
`````````````````````````````````

If the computer you are running Grafana on is not exposed to the internet you
can still access the web interface if you forward port 3000 to your computer.

You will need a way to ssh to the computer you are running on, so hopefully
there is a gateway machine. To make this easier you should add some lines to
your ``.ssh/config``::

    Host gateway
        HostName gateway.ip.address.or.url
        User username

    Host grafana
        HostName ip.address.of.grafana.computer.on.its.network
        User username
        ProxyCommand ssh gateway -W %h:%p

Here you should replace "gateway" and "grafana" with whatever you want, but
note the two locations for "gateway", namely the second in the ProxyCommand.
This will then allow you to ssh through the gateway to "grafana" with a single
command.

You can then forward the appropriate ports by running::

    $ ssh -N -L 3000:localhost:3000 <grafana computer>

You should now be able to access the grafana interface on your computer by
navigating your browser to ``localhost:3000``.


.. _sisock: https://github.com/simonsobs/sisock
.. _Grafana: https://grafana.com/
.. _OCS repo: https://github.com/simonsobs/ocs
.. _ocs-site-config: https://github.com/simonsobs/ocs-site-configs
.. _Docker installation: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _Docker: https://docs.docker.com/v17.09/engine/installation/linux/docker-ce/ubuntu/
.. _post installation: https://docs.docker.com/v17.09/engine/installation/linux/linux-postinstall/
.. _Docker Compose: https://docs.docker.com/compose/install/
.. _spt3g : https://github.com/CMB-S4/spt3g_software
.. _OCS: https://github.com/simonsobs/ocs
