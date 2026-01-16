.. _access_control_dev:

Access Control
==============

This section discusses the implementation of Access Control in Agent
code.  A connected Client will provide a password to the operation,
and this will automatically be compared to the set of accepted
passwords to establish what Privilege Level to use.

From the perspective of the Agent code, there are two ways access can
be restricted:

1. When the Task or Process is registered, on Agent start-up, pass
   ``min_privs=2`` or ``min_privs=3``.  Then, when a client tries to
   start or stop the Operation, any provided password will
   automatically be checked, and the request will be immediately
   rejected.

2. In the body of the Task or Process, the agent code can check the
   current privilege level, and take different actions depending on
   that level.  This is appropriate when certain conditions, which
   need to be assessed on the fly, might warrant requiring a higher
   level of privilege to run.

The next two sections go into more detail on those two approaches.


Restriction of Operations at Agent Start-up
-------------------------------------------

The simplest form of restriction is to simply require a minimum
privilege level for access to a Task or Process.

To restrict access to the Operation Process, state the required access
level in the ``min_privs`` argument when registering the op.  For
example::

  agent.register_task('deep_clean', washingmachine.deep_clean,
                      min_privs=2)

If the need for Access Control depends somewhat on the particular
instance of an Agent, it may be convenient to have ``min_privs`` set
based on a command-line parameter.  The FakeData Agent shows an
example of this.

When restrictions are set up in this way, checking of privileges is
handled automatically and immediately when a client calls ``start`` or
``stop`` on an operation -- if the privileges are not sufficient the
client gets an *immediate* error response indicating the failure.

In the case that an Agent has privilege levels coded in, but you want
to disable (or effectively disable) those restrictions, there are two
simple options:

1. You can run tell the agent to run with no privilege enforcement, by
   passing `--access-policy none`.  In the SCF that would look like
   this::

     {'agent-class': 'FakeDataAgent',
      'instance-id': 'faker4',
      'arguments': [['--access-policy', 'none']],
     },


2. You can add an Access Director configuration block, that accepts an
   empty password for access to level 3::

     passwords:
       - instance_id: 'faker4'
       - password_3: ''


Note that in case (1), the agent will entirely ignore the Access
Director -- so Exclusive Access grants will also not have any effect
on this agent.  In case (2) such grants will still be respected (if
they include a lock-out for general level 3 access).


Dynamic Access Restrictions
---------------------------

A more complex imposition of restrictions is to make run-time
decision, in code.  This is achieved, within the body of the Task or
Process function, by checking ``session.cred_level``.

E.g.::

  class WashingMachine(OCSAgent):
      # ...

      def deep_clean(self, session, args):
          """deep_clean(force=False)

          **Task** -- Perform a deep clean cycle.

          If a normal wash cycle is in progress, cred_level=2 is
          required to start the deep_clean (which will cause the
          current wash cycle to be aborted); in that case force=True
          must be passed.

          """
          if self.wash_cycle_in_progress:
              if session.cred_level < 2 or not force:
                  return False, ("CredLevel=2 and force=True are required "
                                 "to start deep_clean during a wash cycle.")
              self._abort_wash_cycle()

          self.washer._hardware.initiate_deep_clean()
          ...


Note that rejections in the function body cause the Operation to exit
with error, rather than for the ``start`` call of the Operation to
return an immediate error.

It is good practice for an operation to not have drastically different
behavior, depending *only* on the credential level.  Users/clients may
sometimes provide their high-privilege credentials to routine
operations, and safe-guards should remain in place despite that
privileged access.  This is the reason for requiring ``force=True`` in
the ``deep_clean`` example, above -- even a high-privilege user
probably doesn't want, accidentally, to run ``deep_clean`` while the
``wash_cycle_in_progress`` is.


Choosing What to Protect
------------------------

When developing agents with Access Control in mind, you should
consider what functionality of the agent should be restricted.  In a
complex system, operation by users can become very awkward if numerous
different passwords are required to access standard functionality of
various devices.  We thus recommend that Access Control be used only
to guard against the accidental entry into unsafe or highly
inconvenient hardware states.

As a general guideline:

- Require privilege level 3 for operations that could lead to damage,
  long-term outages, or degrade observatory safety.
- Require privilege level 2 for activities that could lead to awkward
  device states that might delay observatory function temporarily, or
  require expert attention to recover from.
- Use default privilege level (1) for everything else.  This is true,
  even if some expertise is required to use the device properly.

Testing and Debugging
---------------------

When testing an agent's Access Control, recall that the
``--access-policy`` argument can be used to set the level 2 and 3
passwords, independent of whether an Access Director agent is running
in the OCS instance.  An example SCF entry for a FakeData agent with
passwords is::

  {'agent-class': 'FakeDataAgent',
   'instance-id': 'faker4',
   'arguments': [['--access-policy', 'override:fake-pw-2,fake-pw-3']],
  },

You can override the ``--access-policy`` on the command line when
using ``ocs-agent-cli``; e.g.::

  $ ocs-agent-cli --instance-id=faker4 --access-policy=none
