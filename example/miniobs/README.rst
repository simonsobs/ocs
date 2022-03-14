Self-contained Test Mini-Observatory
====================================

This example demonstrates operation of a single-host OCS.  The
Observatory consists of the 2 core agents (HostManager and
RegistryAgent), a data aggregation agent (AggregatorAgent), and a
producer of random data (FakeDataAgent).

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

   ocs-local-support generate_crossbar_config


**2. Bringing up the system**

To start up all components of the system, run:

.. code-block:: shell

   ocs-local-support start

This will result in the following things starting up (in order):

- the crossbar server.
- the HostManager Agent instance.
- the HostManager Agent's "manager" Process.
- the child agent instances that are managed by the HostManager in this
  example:

  - Registry
  - Aggregator (this will begin writing an HK archive)
  - FakeData (this will /not/ begin producing data, yet)


Once launched, each of these Agent instances will begin logging to
files in ``logs/``.

**3. Run an acquisition, saving data to data/**

The aggregator will begin writing files automatically on startup.  The
data producer will not generate and send data to the aggregator until
the data production Process is explicitly told to do so.  The script
run_acq.py commands the start of a data production operation, and then
stops it 30 seconds later.  Note that if you interrupt the run_acq.py
script, the agent will keep generating data in the background, and it
will keep being written to disk.  If that happens, run
"ocs-local-support stop" to terminate all agents.

.. code-block:: shell

   python run_acq.py

**4. Bringing down the system**

This ocsbow command stops all the things you started in step 2, in
reverse order.

.. code-block:: shell

   ocs-local-support stop
