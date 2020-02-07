Introduction
============

The goal of OCS is to make it easy to coordinate hardware operation and I/O
tasks in a distributed system such as an astronomical observatory.  The focus
is on ease of use rather than performance.  By "ease of use" we mean that the
learning curve should be shallow; it should be easy for new users to add or
modify components; and the software should run in a variety of environments
(telescope, lab, laptop) without much trouble.  By "rather than performance" we
mean that the system is not intended for real-timey, high throughput, Rube
Goldberg style automation.

Architecture Overview
---------------------
The OCS is a distributed system. Depending on your computing environment and
hardware the configuration can be simple, on a single node, or complex, spread
across multiple nodes. In order to configure your system properly it is helpful
to have a general understanding of the overall construction of the system. In
this section we will give a brief description of the important components.

Agents and Control Clients
```````````````````````````
`Agents` are one of two key elements at the core of OCS. Each Agent interfaces
with a hardware (or software) component to coordinate data acquisition.  These
Agents are long running programs (you can think of them as "servers" in the
software sense) that contain actions referred to as `Tasks` and `Processes`.
These actions perform finite or long running operations, respectively. Calling
of these actions, and the transmission of data collected by them, is done
through a central server known as a WAMP router, in our case specifically the
crossbar server.

Agents by themselves can be configured to run a task or process at startup.
More complicated combinations of actions must be orchestrated by an OCS `Client`.
Because crossbar supports multiple languages, Clients in OCS can take several
forms. Most commonly they will take the form of a python script, run by a user
on the commandline, or the form of Javascript running in your web browser. As a
user you can expect to use existing Agents for common hardware, write new
Agents to accomodate new hardware, use shared Clients to perform tests
identically to other users, and write your own unique Clients to perform tests
in your lab.

Docker
``````
Being a distributed system, OCS is highly flexible in its deployment and
configuration. While it is possible to install ocs and its dependencies
directly on each system, for convenience we recommend the deployment of OCS
components within Docker containers where possible. Docker images for existing
OCS components are available on `Dockerhub <https://hub.docker.com/u/simonsobs>`_.

For more information about Docker we refer here to the Docker documentation:

* `Docker Documentation <https://docs.docker.com/>`_ - General Docker documentation.
* `docker-compose Documentation <https://docs.docker.com/compose/>`_ - docker-compose, for running multi-container applications like OCS.

We will cover basic use of docker and associated commands in the context of
running OCS throughout the guide, but for more details on these and additional
commands the official Docker Documentation is a great resource.
