.. _quickstart:

Quickstart
==========

We'll assume you've already gone through the :ref:`installation` part of the
documentation and thus have installed the required dependencies.

Example Agent/Client
---------------------

Open 3 terminals in the ``example/`` directory. Run the following commands, in
order, one command per terminal::

  make run_crossbar
  make run_agent
  make run_client
  
These will each print out a lot of log messages. But as long as you get more
log messages than error text, you're in good shape.

Web Control Example
-------------------

If the machine where you ran the example also has a GUI, you can open a web
browser and navigate on your local filesystem to the file in the repository
called www/monitor.html. This exposes control buttons and status windows for
the Operations of the Agent that you launched with "make run_agent".
