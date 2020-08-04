================================
OCS - Observatory Control System
================================

.. image:: https://img.shields.io/github/workflow/status/simonsobs/ocs/Build%20Develop%20Images
    :target: https://github.com/simonsobs/ocs/actions?query=workflow%3A%22Build+Develop+Images%22
    :alt: GitHub Workflow Status

.. image:: https://readthedocs.org/projects/ocs/badge/?version=latest
    :target: https://ocs.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/github/simonsobs/ocs/badge.svg
    :target: https://coveralls.io/github/simonsobs/ocs

.. image:: https://img.shields.io/badge/dockerhub-latest-blue
    :target: https://hub.docker.com/r/simonsobs/ocs/tags

Overview
--------

The OCS makes it easy to coordinate hardware operation and I/O tasks in a
distributed system such as an astronomical observatory or test laboratory. OCS
relies on the use of a central WAMP router (currently `crossbar.io`_) for
coordinating the communication and control of these distributed systems.

The OCS provides Python (and JavaScript) functions and classes to allow
"Clients" to talk to "Agents". An Agent is a software program that knows how to
do something interesting and useful, such as acquire data from some device or
perform cleanup operations on a particular file system. A Control Client could
be a web page with control buttons and log windows, or a script written by a
user to perform a series of unattended, interlocking data acquisition tasks.

This repository, `OCS`_, contains library code and core system
components.  Additional code for operating specific hardware can be
found in the `Simons Observatory Control System (SOCS)`_ repository.
Grafana and InfluxDB are supported to provide a near real-time monitoring and
historical look back of the housekeeping data.

.. _crossbar.io: http://crossbario.com
.. _`OCS`: https://github.com/simonsobs/ocs/
.. _`Simons Observatory Control System (SOCS)`: https://github.com/simonsobs/socs/

Dependencies
------------

This code targets Python 3.5+.

There are also several Python package dependencies, which are listed in the
`requirements.txt`_ file.

.. _requirements.txt: requirements.txt

Installation
------------
Clone this repository and install using pip::

  git clone https://github.com/simonsobs/ocs.git
  cd ocs/
  pip3 install -r requirements.txt
  python3 setup.py install

**Note:** If you want to install locally, not globally, throw the `--user` flag
on both the pip3 and setup.py commands.

**Warning:** The master branch is not guaranteed to be stable, you might want
to checkout a particular version tag before installation depending on which
other software you are working with. See the latest `tags`_.

.. _tags: https://github.com/simonsobs/ocs/tags

Docker Images
-------------
Docker images for OCS and each Agent are available on `Docker Hub`_. Official
releases will be tagged with their release version, i.e. ``v0.1.0``. These are
only built on release, and the ``latest`` tag will point to the latest of these
released tags. These should be considered stable.

Development images will be tagged with the latest released version tag, the
number of commits ahead of that release, the latest commit hash, and the tag
``-dev``, i.e.  ``v0.6.0-53-g0e390f6-dev``. These get built on each commit to
the ``develop`` branch, and are useful for testing and development, but should
be considered unstable.

.. _Docker Hub: https://hub.docker.com/u/simonsobs

Documentation
-------------
The OCS documentation can be built using sphinx once you have performed the
installation::

  cd docs/
  make html

You can then open ``docs/_build/html/index.html`` in your preferred web
browser. You can also find a copy hosted on `Read the Docs`_.

.. _Read the Docs: https://ocs.readthedocs.io/en/latest/

Example
-------

A self contained example, demonstrating the operation of a small observatory
with a single OCS Agent is contained in `example/miniobs/`_.  See the `readme`_
in that directory for details.

.. _example/miniobs/: example/miniobs/
.. _readme: example/miniobs/README.rst

Contributing
------------
For guidelines on how to contribute to OCS see `CONTRIBUTING.rst`_.

.. _CONTRIBUTING.rst: CONTRIBUTING.rst

License
--------
This project is licensed under the BSD 2-Clause License - see the
`LICENSE.txt`_ file for details.

.. _LICENSE.txt: LICENSE.txt
