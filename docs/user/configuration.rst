.. highlight:: rst

System Configuration
====================

There are two types of configuration files that are important to OCS.
Each system will have a single OCS Site Config File (SCF), and
probably one (or more) Docker Compose config file(s).  These two files
organize and configure a site's OCS Agents and supporting docker
containers.

Site operators may also need to alter the configuration of the
crossbar router, and to set up systems for centralized management of
OCS Agents even when they are running on a variety of hosts.

Details about each of these configuration files are discussed in the
following pages:

.. toctree::
    :maxdepth: 2

    site_config
    docker_config 
    crossbar_config
    centralized_management
