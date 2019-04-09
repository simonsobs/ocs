Self-contained Test Mini-Observatory
====================================

This example demonstrates operation of a single-host OCS.  The
Observatory consists of the 2 core agents (HostMaster and
RegistryAgent), a data aggregation agent (AggregatorAgent), and a
custom data producer defined here (FakeDataAgent).

The site_config file, ``default.yaml``, demonstrates a few practices
that are not generally a good idea in any kind of "production" setup.
In particular:

- The list of Agents is defined under hostname ``localhost``.  This is
  a wildcard that can only work in a single-host system.
- ``log-dir``, ``agent-paths``, and the ``crossbar:config-dir`` are
  all specified as relative paths.  Behavior will be unpredictable if
  Agents are not all invoked in the same working directory.

The steps below are also grouped into targets in a ``Makefile`` in
this directory.


**0. Prior to any session**

This example assumes that the ``ocs`` python module can be imported,
and that the ``ocsbow`` binary is in the binary path.  Both of these
should be true if you installed the package to a local or system level
folder.

This example is configured so that you can ``cd`` directly to the
example directory (where this README is located) and run commands from
there.  However, you still need to tell OCS to refer to the local
configuration file, ``default.yaml``.  The recommended approach is to
temporarily define the environment variable:

.. code-block:: shell

   export OCS_CONFIG_DIR=`pwd`

An alternative is to pass ``--site-file=default.yaml`` to *every*
invocation of ocsbow, as well as to the ``run_acq.py`` script.


**1. First-time set-up**

These setup commands create the required directory structure and a
configuration file for crossbar.

.. code-block:: shell

   mkdir dot_crossbar
   mkdir logs
   mkdir data

   ocsbow crossbar generate_config > dot_crosssbar/config.json


**2. Bringing up the system**

These commands will start up the crossbar server, the HostMaster, and
then the other Agents defined in default.yaml.  After ``launch`` the
HostMaster agent will log to the file ``logs/observatory.hm1.log``.
After ``start``, the other agents will log to other files in that
directory.

.. code-block:: shell

   ocsbow crossbar start
   ocsbow launch
   ocsbow start

**3. Run an acquisition, saving data to data/**

The data producer and aggregator agents start up in an idle state.
The run_acq.py script starts the right agent Operations to obtain a 30
second acquisition.

.. code-block:: shell

   python run_acq.py

**4. Bringing down the system**

These ocsbow commands undo the ones from step 2, in reverse order.

.. code-block:: shell

   ocsbow stop
   ocsbow unlaunch
   ocsbow crossbar stop
