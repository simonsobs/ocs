.. _access_control_user:

Access Control
==============

In OCS, Access Control is a set of features to restrict some Agent
activities, so that they can only be controlled by certain privileged
clients.  The goals of the Access Control system are:

- Provide a way to restrict some Agent functionality, such as
  dangerous or time consuming operations, to clients or users that
  have provided special access passwords.
- Provide a way for special clients, such as the main observatory
  scheduling system, to request exclusive access to Agent functions,
  and thus prevent other clients from initiating potentially
  interfering activities.

To enable the full features of OCS Access Control, it is necessary to
include an instance of the :ref:`Access Director<access_director>`
Agent in the OCS setup.  The Access Director distributes access
information to Agents on the network using a special feed, and
processes requests from agents and clients using special WAMP access
points.


Important configuration files
-----------------------------

Access Control is affected by the following configuration files:

**Site Config File**

- The SCF includes a global setting that determines whether agents in
  the system should refer to the Access Director (AD) agent, or not.
  See :class:`ocs.site_config.HubConfig`.
- The SCF also must include a block that sets up an instance of the
  AD, which will include specifying the path to the Access Config
  File; see :ref:`Access Director<access_director>`.

**Access Config File**

- The Access Config File is a YAML file read by the AD.  It sets the
  passwords that clients can use to obtain different credential levels
  for different agent instances.
- It may also define "Exclusive Access" grant blocks (see below).
- The format of this file, too, is described with the :ref:`Access
  Director<access_director>` Agent.


**Client Access Config Files**

- Although you can include passwords when instantiating
  :class:`ocs.ocs_client.OCSClient` objects, users can store passwords in
  a config file for automatic retrieval.
- See :ref:`clients_passwords`.


Setting up the Access Director
------------------------------

The Access Director agent is set up just like any other agent, with an
entry in the Site Config File.  See the Agent's instructions for the
standard SCF and docker-compose blocks.  Because it will be critical
to proper functioning of OCS, it is a good idea to configure it to run
on the same host as the crossbar server and other critical agents
(Registry, Aggregator) if possible.


Setting up Agents to Listen to the Access Director
--------------------------------------------------

By default, other Agents will not know to refer to the Access Director
for access information.  Agents need to be configured to refer to the
Access Director, by either:

- Passing the ``--access-policy=director:<instance-id>`` argument to
  the Agent, providing the instance-id of the Access Director;  OR
- The ``'access_policy'`` setting in the SCF, which sets the default
  value for `--access-policy` argument for all agents in the OCS
  instance.

Before enabling the "director" access policy on the whole system, the
behavior can be tested on a subset of Agents by passing
``--access-policy`` explicitly in their instance args.

Once an Agent instance has been launched with
``--access-policy=director...``, communication with the instance *will
depend on* the presence and proper functioning of the Access Director
agent on the network.  (Without such stringent policies, the power of
exclusive access grants would be diminished.)


Developing Agents with Access Control Features
----------------------------------------------

In most cases it will be necessary to include access controls
(e.g. requiring a specific level to perform a certain task) in the
Agent code.  See :ref:`access_control_dev`.

For agents that do not have any explicit Access Control functionality
built in, they are still subject to constraints from the Accesss
Director -- provided that the Agent instance is running on a version
of ``ocs`` that is Access Control-aware.  Even if an agent doesn't set
any minimum credential levels for operations, the Access Director can
still restrict access to that agent by imposing passwords for level 1
access.


Passwords and Credential Levels
-------------------------------

The basic approach to access control is that a client will provide a
password whenever it performs calls to an Agent Instance Operation
(e.g. starting a Task).  Based on the password, the client will be
granted some level of access.  The access levels are:

- 0: Access is blocked.
- 1: Basic Access.
- 2: Advanced Access.
- 3: Full Access.
- 4: Super-user Access.

Operations within the Agent Instance will be hard-coded, or will
somehow decide dynamically, to require some minimum access level to
perform a given operation.  If the access level associated with the
password is equal to or higher than the required access level, then
the operation is allowed to proceed.  Otherwise, the call will return
an error immediately (or, in dynamically decided cases, the operation
will exit with error).

For details on how to add Credential Level awareness to Agent code,
see :ref:`access_control_dev`.


Exclusive Access Grants
-----------------------

Exclusive Access Grants are a means for some clients to obtain
exclusive access to certain operations.  For example, a sequence of
activities that requires careful interleaving of otherwise routine
tasks between two agents might request exclusive access to those two
agent instances, locking out all other users.

Multiple Exclusive Access Grant blocks can be defined, in the Access
Config File, and then may be referenced by "name" and activated by
providing a (optional) password to the Access Director agent.

For a description of the Exclusive Access Grant block format, see
:ref:`access_director_config_file`.  For details on how a client may
request, renew, and relinquish an Exclusive Access Grant, see
:class:`ocs.access.ExclusiveAccessClient`.
