Observatory Control System (OCS)
================================

The goal of OCS is to make it easy to coordinate hardware operation and i/o
tasks in a distributed system such as an astronomical observatory.  The focus
is on ease of use rather than performance.  By "ease of use" we mean that the
learning curve should be shallow; it should be easy for new users to add or
modify components; and the software should run in a variety of environments
(telescope, lab, laptop) without much trouble.  By "rather than performance" we
mean that the system is not intended for real-timey, high throughput, Rube
Goldberg style automation.

The OCS provides python (and javascript) functions and classes to allow
"Control Clients" to talk to "Agents".  An Agent is a software program that
knows how to do something interesting and useful, such as acquire data from
some device or perform cleanup operations on a particular file system. A
Control Client could be a web page with control buttons and log windows, or a
script written by a user to perform a series of unattended, interlocking data
acquisition tasks.


User's Guide
------------

This part of the documentation begins with some background information about
OCS.

.. toctree::
   :maxdepth: 2

   architecture
   installation
   quickstart
   lakeshore372

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
