================================
OCS - Observatory Control System
================================

| |pypi| |versions| |docker| |license|
| |tests| |pre-commit| |coverage| |docs|

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

This code targets Python 3.7+.

* `so3g`_ - Required for using the HK Aggregator Agent.
* `crossbar`_ (optional) - The supported WAMP router. Controllable via
  `ocsbow`. Can be installed with pip
  or run via Docker.

.. _so3g: https://github.com/simonsobs/so3g
.. _crossbar: https://pypi.org/project/crossbar/

Installation
------------

Install and update with pip::

    $ pip3 install -U ocs

If you need to install the optional so3g module you can do so via::

    $ pip3 install -U ocs[so3g]

Installing from Source
``````````````````````

If you are considering contributing to OCS, or would like to use an unreleased
feature, you will want to install from source. To do so, clone this repository
and install using pip::

  $ git clone https://github.com/simonsobs/ocs.git
  $ cd ocs/
  $ pip3 install -r requirements.txt
  $ pip3 install .

**Note:** If you want to install locally, not globally, throw the `--user` flag
on the pip3 commands.

Docker Images
-------------
Docker images for OCS and each Agent are available on `Docker Hub`_. Official
releases will be tagged with their release version, i.e. ``v0.1.0``. These are
only built on release, and the ``latest`` tag will point to the latest of these
released tags. These should be considered stable.

Test images will be tagged with the latest released version tag, the number of
commits ahead of that release, the latest commit hash, i.e.
``v0.6.0-53-g0e390f6``. These get built on each commit to the ``main`` branch,
and are useful for testing and development, but should be considered unstable.

.. _Docker Hub: https://hub.docker.com/u/simonsobs

Documentation
-------------
The OCS documentation can be built using Sphinx. There is a separate
``requirements.txt`` file in the ``docs/`` directory to install Sphinx and any
additional documentation dependencies::

  $ cd docs/
  $ pip3 install -r requirements.txt
  $ make html

You can then open ``docs/_build/html/index.html`` in your preferred web
browser. You can also find a copy hosted on `Read the Docs`_.

.. _Read the Docs: https://ocs.readthedocs.io/en/latest/

Tests
-----
The tests for OCS can be run using pytest, and should be run from the
``tests/`` directory::

  $ cd tests/
  $ python3 -m pytest

To run the tests within a Docker container (useful if your local environment is
missing some dependencies), first make sure you build the latest ocs image,
then use docker run::

  $ docker build -t ocs .
  $ docker run --rm -w="/app/ocs/tests/" ocs sh -c "python3 -m pytest -m 'not integtest'"

For more details see `tests/README.rst <tests_>`_.

.. _tests: https://github.com/simonsobs/ocs/blob/main/tests/README.rst

Example
-------

A self contained example, demonstrating the operation of a small observatory
with a single OCS Agent is contained in `example/miniobs/`_.  See the `readme`_
in that directory for details.

.. _example/miniobs/: https://github.com/simonsobs/ocs/tree/main/example/miniobs
.. _readme: https://github.com/simonsobs/ocs/blob/main/example/miniobs/README.rst

Contributing
------------
For guidelines on how to contribute to OCS see `CONTRIBUTING.rst`_.

.. _CONTRIBUTING.rst: https://github.com/simonsobs/ocs/blob/main/CONTRIBUTING.rst

License
--------
This project is licensed under the BSD 2-Clause License - see the
`LICENSE.txt`_ file for details.

.. _LICENSE.txt: https://github.com/simonsobs/ocs/blob/main/LICENSE.txt


.. |coverage| image:: https://coveralls.io/repos/github/simonsobs/ocs/badge.svg
    :target: https://coveralls.io/github/simonsobs/ocs

.. |docker| image:: https://img.shields.io/badge/dockerhub-latest-blue
    :target: https://hub.docker.com/r/simonsobs/ocs/tags

.. |docs| image:: https://readthedocs.org/projects/ocs/badge/?version=main
    :target: https://ocs.readthedocs.io/en/main/?badge=main
    :alt: Documentation Status

.. |license| image:: https://img.shields.io/pypi/l/ocs
    :target: LICENSE.txt
    :alt: PyPI - License

.. |pre-commit| image:: https://results.pre-commit.ci/badge/github/simonsobs/ocs/main.svg
    :target: https://results.pre-commit.ci/latest/github/simonsobs/ocs/main
    :alt: pre-commit.ci status

.. |pypi| image:: https://img.shields.io/pypi/v/ocs
    :target: https://pypi.org/project/ocs/
    :alt: PyPI Package

.. |tests| image:: https://img.shields.io/github/actions/workflow/status/simonsobs/ocs/develop.yml?branch=main
    :target: https://github.com/simonsobs/ocs/actions?query=workflow%3A%22Build+Test+Images%22
    :alt: GitHub Workflow Status

.. |versions| image:: https://img.shields.io/pypi/pyversions/ocs
    :alt: PyPI - Python Version
