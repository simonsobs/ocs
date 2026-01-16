.. highlight:: rst

.. _access_director:

=====================
Access Director Agent
=====================

The Access Director Agent distributes Access Control information
(passwords) to all subscribed agents in the OCS instance.  See the
main article on :ref:`access_control_user`, and the Agent
:ref:`access_director_description` below.


.. argparse::
   :module: ocs.agents.access_director.agent
   :func: make_parser
   :prog: agent.py



Configuration File Examples
---------------------------

OCS Site Config
```````````````

To configure the Access Director Agent we need to add an AccessDirector
block to our ocs configuration file. Here is an example configuration
block using all of the available arguments::

    {'agent-class': 'AccessDirector',
     'instance-id': 'access-dir',
     'arguments': ['--config-file', '/config/access-director.yaml']}

Docker Compose
``````````````

The Access Director Agent can also be run in a Docker container. An
example docker-compose service configuration is shown here::

    ocs-access-dir:
        image: simonsobs/ocs:latest
        hostname: ocs-docker
        environment:
          - LOGLEVEL=info
          - INSTANCE_ID=access-dir
        volumes:
          - ${OCS_CONFIG_DIR}:/config:ro

.. _access_director_config_file:

Access Director Configuration File
``````````````````````````````````

The format is described below, but for a browsable schema see
:class:`ocs.access.AccessDirectorConfig`.

Here is an example configuration file:

.. code-block:: yaml

  # Policy file for OCS Access Directory Agent

  passwords_block_default_hashfunc: none
  distrib_hashfunc: md5

  passwords:
    - default: true
      password_4: 'superuserPassword!'
    - agent_class: 'FakeDataAgent'
      instance_id: '!faker4'
      password_2: 'fake2ser'
    - instance_id: 'faker4'
      password_2: 'specialLevel2'
      password_3: 'speciallevel3'

  exclusive_access_blocks:
    - name: "the-fakers"
      password: "lockout-test"
      grants:
      - instance_id: "faker4"
        lock_levels: [1,2,3]
        cred_level: 1
      - instance_id: "faker*,!faker4"
        lock_levels: [3]
        cred_level: 3


The ``passwords`` entry is a list of password assignment blocks, which
define passwords that should grant clients certain credential levels
on certain agents.

The syntax of the assignment blocks is described in
:class:`ocs.access.AccessPasswordItem`.

**Examples**

Example 1 -- set the level (1,2,3,4) passwords for all agents to ('', 'special2',
'special3', 'superuser')::

  passwords:
    - default: true
      password_1: ''
      password_2: 'special2'
      password_3: 'special3'
      password_4: 'superuser'

Example 2 -- like Example 1 except that any agent with the class
"FakeDataAgent" will have level 2 password set to 'fake2'::

  passwords:
    - default: true
      password_1: ''
      password_2: 'special2'
      password_3: 'special3'
      password_4: 'superuser'
    - agent_class: FakeDataAgent
      password_2: 'fake2'

Example 3 -- like Example 2 except that the agent with `instance_id`
of "danger4" will have the level 2 and level 3 access totally
disabled (even if "danger4" is a FakeDataAgent.)::

  passwords:
    - default: true
      password_1: ''
      password_2: 'special2'
      password_3: 'special3'
      password_4: 'superuser'
    - agent_class: FakeDataAgent
      instance_id: '!danger4'
      password_2: 'fake2'


**exclusive_access_blocks**

The ``exclusive_access_blocks`` entry is a list of access grant
blocks.  Each block must at least have a (unique) "name" entry, and a
list of :class:`GrantConfigItem<ocs.access.GrantConfigItem>`.  Each
GrantConfigItem targets some set of agent instances (using the
`default` / `agent_class` / `instance_id` keys in the same way that
:class:`ocs.access.AccessPasswordItem` does).  The `cred_level`
declares what level to give the grantee, on the targeted instances.
The `lockout_levels` is a list of Credential Levels to *lock out*,
during this grant.

The additional settings items are:

- ``passwords_block_default_hashfunc``: name of the hash function to
  assume for passwords provided in the "passwords" block.  (Default:
  "none", meaning they are the cleartext.)
- ``distrib_hashfunc``: hashfunc to use, instead of cleartext, when
  distributing passwords to agents.  (Does not affect passwords that
  were provided already hashed.)



.. _access_director_description:


Description
-----------

The role of this Agent is to distribute Access Control information to
Agent Instances and Clients in the OCS instance.  In an OCS there will
normally be zero or one instance of the Access Director (but it's
possible to set up multiple instances, and have different agents
attuned to different Access Directors).

The agent configuration is provided through the Access Config File,
the path to which is a command-line parameter.  The ``manager``
process distributes access information to agents on a special feed
(``...feeds.controls``).  The task ``reload_config`` may be used to
trigger a reload of the config file.  If there are syntax errors in
the config file, this will normally cause the reload to be ignored and
the existing configuration to persist.

Two "special access points" are exposed by the Access Director.  The
``agent_poll`` method is used by agents to request an update of their
current access information; they will normally do this when they
connect or reconnect to crossbar.

The ``request_exclusive`` access point is used by clients that wish to
establish an Exclusive Access Lock.  The client would provide the name
of the access block, and a password (if defined).  The Agent then
returns to that client a randomly generated password that the client
can use to talk to all agents covered by the grant.  Starting then,
and until the grant expires or is released, the Agent distributes
updated access information to all agents that reflects the new access
rules -- i.e. special access levels, granted based on that password,
and also any lock-outs that are associated with the grant.


Agent API
---------

.. autoclass:: ocs.agents.access_director.agent.AccessDirector
    :members:
