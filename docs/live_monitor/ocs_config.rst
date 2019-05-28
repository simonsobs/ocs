.. highlight:: rst

OCS
---

Site configuration is described over on the page :ref:`site_config`. Here we will
look at the ``templates/ocs_template.yaml`` config as an example. (Note, you
should rename the template to be ``<your institution>.yaml``)::

    # Site configuration for a fake observatory.
    hub:
    
      wamp_server: ws://localhost:8001/ws
      wamp_realm: test_realm
      address_root: observatory
      registry_address: observatory.registry
    
    hosts:
    
      hostname: {
    
        # Description of a host's Agents.
    
        'agent-instances': [
          {'agent-class': 'Lakeshore372Agent',
           'instance-id': 'LSA22YE',
           'arguments': [['--serial-number', 'LSA22YE'],
                         ['--ip-address', '10.10.10.4']]},
          {'agent-class': 'Lakeshore240Agent',
           'instance-id': 'ls240',
           'arguments': [['--serial-number', 'LSA22ZC']]},
          {'agent-class': 'AggregatorAgent',
           'instance-id': 'aggregator',
           'arguments': []},
          {'agent-class': 'RegistryAgent',
           'instance-id': 'registry',
           'arguments': []},
        ]
    }

All of the information in the ``hub:`` section should remain unchanged, unless
you know what you're doing.

Under ``hosts:`` you'll need to replace ``hostname`` with the name of your
computer. If you don't know your computer's name, open a terminal and type
``hostname``, enter whatever comes out.

Each item under a given host describes the OCS Agents which may be run. For
example we'll look at the first 372 Agent here::

          {'agent-class': 'Lakeshore372Agent',
           'instance-id': 'LSA22YE',
           'arguments': [['--serial-number', 'LSA22YE'],
                         ['--ip-address', '10.10.10.4']]},

The ``agent-class`` is given by the actual Agent we'll be running. This must
match the name defined in the Agent's code. The ``instance-id`` is a unique
name given to this agent instance. Here we use the Lakeshore 372 serial number.
This will need to be noted for later use in the live monitoring. Finally the
arguments are used to pass default arguments to the Agent at startup, which
contains the serial number again as well as the IP address of the 372.

In order for OCS to know where to find your configuration file we need to take
two more steps. First, add the following to your ``.bashrc`` file::

    export OCS_CONFIG_DIR='/path/to/ocs-site-configs/<your-institution-directory>/'

Next, symlink your configuration file to ``default.yaml``::

    $ ln -s yale.yaml default.yaml

If you're proceeding in the same terminal don't forget to source your
``.bashrc`` file.

For more information see the :ref:`site_config` page in this documentation.
