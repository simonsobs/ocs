.. highlight:: rst

Environment Setup
=================

All the required software should now be installed. The next step is to properly
configure the environment. Scripts to help with parts of this setup are
provided in the ocs-site-config_ repository. In this repository is a directory
for each SO site, currently this means one for each test institution (i.e.
yale, penn, ucsd). Start by cloning this repository, and if your site does not
have a directory, copy the templates directory to create one.::

    $ git clone https://github.com/simonsobs/ocs-site-configs.git
    $ cp -r templates/ yale/

Setup Scripts
-------------
There are many steps to perform in setting up a new system. In an attempt to
streamline these setup steps we have provided several setup scripts. These need
to each be run once on your system. In the future they will likely be combined
into a single script, but for now we deal with the individual parts.

TLS Certificate Generation
``````````````````````````
The crossbar server can handle secure connections using TLS certificates. The
live monitor uses this secure connection capability, and as a result we need to
generate a set of self-signed TLS certificates. To do this we just need to run
the ``setup-tls.sh`` script. Simply enter your new directory and run it (swap
``yale`` for your institution)::

    $ cd yale/
    $ ./setup-tls.sh

This will generate the required certificates and put them in a directory called
``.crossbar/`` (which already existed in the copied template directory). 

.. warning::

    Make sure your ``.crossbar/config.json`` file exists. Missing the dot
    directory when copying files from the template is a common mistake. A
    missing crossbar configuration will cause the entire system not to work.

.. _ocs-site-config: https://github.com/simonsobs/ocs-site-configs

Docker Environment Setup
````````````````````````
If this is your first time using Docker then we need to do some first time
setup. In the site-config ``templates/`` directory (and thus in your copy of it
for your institution) there should be a script called ``init-docker-env.sh``.
Running this creates a storage volume for Grafana so that any configuration we
do survives when we remove the container. To setup the Docker environment run
the script::

    $ sudo ./init-docker-env.sh

Manual Setup Steps
------------------
These steps haven't been included in any scripts yet, and must be performed
manually. These only need to be performed once per system.

OCS User/Group and Data Directory Creation
``````````````````````````````````````````
The OCS aggregator agent runs as a user called `ocs`, with a UID of 9000. We
will setup the same `ocs` user on the host system, as well as an `ocs` group.
The data written by the aggregator will belong to this user and group::

    $ groupadd -g 9000 ocs 
    $ useradd -u 9000 -g 9000 ocs 

Next we need to create the data directory which the aggregator will write files
to. This can be any directory, however we suggest using ``/data``, and will use
this in our example::

    $ mkdir /data
    $ chown 9000:9000 /data

Finally, we should add the current user account to the `ocs` group, replace
`user` with your current user::

    $ sudo usermod -a -G ocs user

OCS Config Setup
````````````````
The OCS configuration file is named after a given site, i.e. ``yale.yaml``. In
order for OCS to know where to find your configuration file we need to do two
things.

First, add the following to your ``.bashrc`` file::

    export OCS_CONFIG_DIR='/path/to/ocs-site-configs/<your-institution-directory>/'

Next, within your site config directory, symlink your configuration file to
``default.yaml``::

    $ ln -s yale.yaml default.yaml

.. note::
    If you're proceeding in the same terminal don't forget to source your
    ``.bashrc`` file.

Login to Docker Registry
````````````````````````
The Docker images which we will need to run the live monitor are hosted on a
private Docker registry at Yale. Until things are hosted publicly we need to
login to the private. (The password can be found on the `SO wiki
<http://simonsobservatory.wikidot.com/tech:daq:credentials>`_.) To do so run::

    $ sudo docker login grumpy.physics.yale.edu
    Username: simonsobs
    Password: 

You will see output along the lines of::

    WARNING! Your password will be stored unencrypted in /home/user/.docker/config.json.
    Configure a credential helper to remove this warning. See
    https://docs.docker.com/engine/reference/commandline/login/#credentials-store
    
    Login Succeeded

You will now be able to pull images from the registry.

The system is now ready to configure. In the next section we will discuss both
the `docker-compose` and `ocs` configuration files.
