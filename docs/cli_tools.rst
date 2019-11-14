.. highlight:: bash

.. _cli_tools:

=========
CLI Tools
=========

Several CLI tools are provided with OCS. This page describes these tools, what
they are used for, and how to use them.

ocsbow 
======

(The output from ``ocsbow --help`` should be rendered here.)

.. argparse::
   :module: ocs.ocsbow
   :func: get_parser
   :prog: ocsbow

checkdata
=========

``checkdata`` is a CLI tool for quickly viewing the most recent times each
agent instance-id's feeds and associated fields were seen in the data written
to disk. This is meant as a quick way to check on the state of data
aggregation.

.. note::
    `checkdata` will open all files within a directory, walking as deep as it
    needs to to find all .g3 files within. It's recommended not to run it on an
    entire data output directory, unless you want to wait for a long time.
    Instead, you should probably just run it on a single day's directory, or
    even individual file, depending on your needs.

.. note::
    If so3g is not installed on your system, `checkdata` will use a docker
    image. This will require permissions to interact with docker.

For info on how to run, see the help::

    $ checkdata -h
    usage: checkdata [-h] [--verbose] [--docker] target
    
    positional arguments:
      target         File or directory to scan.
    
    optional arguments:
      -h, --help     show this help message and exit
      --verbose, -v
      --docker, -d   Force use of docker, even if so3g is installed.

Usage/Examples
--------------
To use ``checkdata`` simply invoke it on the commandline::

    $ checkdata /data/15732/
    Scanning |################################| 11/11 Processing |################################| 156/156
    
    LSA22YE
      temperatures: 643.6 s old
    
    LSA22YG
      temperatures: 727.9 s old
    
    LSA22Z2
      temperatures: 310.0 s old
    
    LSA22ZC
      temperatures: 318.9 s old
    
    LSA24R5
      temperatures: 286.6 s old
    
    LSA2761
      temperatures: 355.4 s old
    
    bluefors
      bluefors: 371.3 s old

.. note::
    This assumes ``checkdata`` is in your user's ``$PATH``.

This presents each agent, the agent's feeds, and a time representing the oldest
field within that feed. For more verbose output, throw the ``-v`` flag::

    $ checkdata -v /data/15732/2019-11-08-10-35-29.g3
    Scanning |################################| 1/1
    Processing |################################| 156/156
    
    LSA22YG
      temperatures
      -----------------------------------------------------------------------------------------
                     Field |    Last Seen [s ago] |      Seen At [ctime] |                Value
      -----------------------------------------------------------------------------------------
              Channel 01 R |                320.4 |   1573212564.6585813 |              29255.1
              Channel 01 T |                320.4 |   1573212564.6585813 |            0.0656435

