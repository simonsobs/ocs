Next Steps 
----------

You now have a working OCS Agent! What's next? Well, while this Agent works,
you probably need to do more than just print text and count integers. Working
from this example, you will need to add communication with your piece of
hardware, data processing, and more.

Often it is convenient to create a separate class or external driver file (or
even import one that already provides that functionality) that the Agent can
use to interface with a hardware device. Examples of this can be seen in
existing OCS Agents. Two good sources of examples are:

* `ocs/agents/`_ -  Core OCS Agents
* `socs/agents/`_ - Simons Observatory control system Agents

While core OCS doesn't have any Agents that interface with hardware, there are
examples of handling data being published to feeds (and doing that handling in
separate classes imported from other modules) in both the HK Aggregator Agent
and InfluxDB Publisher Agent.

.. _ocs/agents/: https://github.com/simonsobs/ocs/tree/develop/agents
.. _socs/agents/: https://github.com/simonsobs/socs/tree/develop/agents

Add to Agent List
`````````````````

We can run our Agent directly, or within Docker, but in order for the Host
Manager Agent to know where to find your Agent you must add the Agent to the
ocs plugin file. Many Agents tend to live in a single repo split by experiment,
each one of which should contain an ``ocs_plugin_<experiment>.py`` file. This
script registers all of the agents so that Host Manager can start and stop
them. An example (of the standard ocs library plugin file) is shown here:

.. include:: ../../agents/ocs_plugin_standard.py
    :code: python

Development Tips
````````````````

This section contains miscellaneous development tips for working on OCS Agents.
If you have a tip you found useful while working on an Agent, feel free to open
a PR adding it to this page!

Developing and Docker
^^^^^^^^^^^^^^^^^^^^^

Docker is great for deploying many copies of Agents with complicated
dependencies to many different sites, however it does slow down development, as
you are often rebuilding images. It can be easier to work on your Agent outside
of Docker, running it directly on the host system, then, once the Agent is
working, build the Docker image and test it.

Another approach is to still use Docker (maybe you need some of those
complicated dependencies on your development system as well and it's the most
convenient way to get them), but to mount the code you're working on over the
copy used within the container. This requires an understanding of how files are
stored within the container. Once you are done you should still build and run
the image to test without your mounted code.
