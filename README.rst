================================
OCS - Observatory Control System
================================

Overview
========

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

.. _crossbar.io: http://crossbario.com

Dependencies
------------
* python >= 3.5

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

Documentation
-------------
The OCS documentation can be built using sphinx once you have performed the
installation::

  cd docs/
  make html

You can then open ``docs/_build/html/index.html`` in your preferred web
browser.


Example
-------

A self contained example, demonstrating the operation of a small observatory
with a single OCS Agent is contained in `example/miniobs/`_.  See the `readme`_
in that directory for details.

.. _example/miniobs/: example/miniobs/
.. _readme: example/miniobs/README.rst

License
--------
This project is licensed under the BSD 2-Clause License - see the
`LICENSE.txt`_ file for details.

.. _LICENSE.txt: LICENSE.txt
