.. _param:

Operation Parameters
--------------------

Many Tasks and Processes will have parameters that are passed in from
a client when the Operation is inititated.  These are presented to the
Operation function as the second argument, the ``params`` dictionary.
The signature of Task and Process start functions is::

   operation_name(self, session, params)

Validation using @param
^^^^^^^^^^^^^^^^^^^^^^^

It is recommended that Agent developers use the
:func:`ocs.ocs_agent.param` function decorator to describe all of the
parameters that are accepted by an Operation start function.

An example of this can be found in the FakeDataAgent::

    @ocs_agent.param('delay', default=5., type=float, check=lambda x: 0 < x < 100)
    @ocs_agent.param('succeed', default=True, type=bool)
    @inlineCallbacks
    def delay_task(self, session, params):

(Note that ``@inlineCallbacks`` is a Twisted thing that is not part of
parameter decoration.)

Using decorators is optional, but provides benefits to both the Agent
developer and to the user on the Client side.  For the developer, the
Operation code (the ``delay_task`` function body) may now assume that:

- ``params['delay']`` is set and contains a float with a value between
  0 and 100.
- ``params['succeed']`` is set and is a bool.
- There are no other keys in ``params``.

For the user, any attempt to launch this Operation with invalid
parameters (e.g. ``delay="seven"`` or ``random_word="brgla"``) will be
immediately rejected, producing an informative error message::

  >>> client.delay_task(delay='seven')
  OCSReply: ERROR : Param 'delay'=seven is not of required type (<class 'float'>)
    (no session -- op has never run)

When using decorators, you have to describe *all* the accepted
parameters.  The client will be blocked from passing any undefined
parameters.  To override that behavior (and allow undeclared
parameters to sail through to the agent), add
``@ocs_agent.param('_no_check_strays')`` to your decorator set.

If you have a function that accepts no parameters, decorate it with
``@ocs_agent.param('_')``; that will raise an error for the client if
they try to pass anything in params.

Here are a few more examples of decorator usage:

  *Require that value passed in has a certain type*::

    @ocs_agent.param('name', type=str)  # Accepts '1.0' but rejects float 1.0

  *Convert incoming data using some casting function*::

    @ocs_agent.param('name', cast=float)  # Accepts '1.0', converts it to float 1.0

  *Require the value to be drawn from a limited set of
  possibilities*::

    @ocs_agent.param('mode', choices=['current', 'voltage'])  # Rejects other values

  *Require the value to be between 0 and 24; note that if the check
  fails, the error message returned to user won't be detailed... it
  will simply say that a validity check failed.  The docstring has to
  pick up the slack there.*::

    @ocs_agent.param('voltage', check=lambda x: 0 <= x <= 24)

  *If the data is passed in, it must be an integer.  But if not passed
  in, default to None.*::

    @ocs_agent.param('repeat', default=None, type=int)


Validation in the Op function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the case that more complicated parameter processing is required,
the Operation code can raise the special
:class:`ocs.ocs_agent.ParamError` exception to signal failures related
to parameter processing.  This exception will be caught by the
encapsulating code and logged as a special failure rather than a
general crash of the thread.

Here's an example of the implementation in the Agent, for the
FakeDataAgent ``delay_task``::

  def delay_task(self, session, params):
      try:
          delay = float(params.get('delay', 5))
      except ValueError:
          raise ocs_agent.ParamError("Invalid value for parameter 'delay'")

The @params decorator could have been used in such a simple case.
In-operation param checking is still necessary sometimes; consider
this example where the acceptable values of the `'setpoint`' param
depend on the value the `'mode'` param::

  @ocs_agent.param('mode', choices=['voltage', 'current'])
  @ocs_agent.param('setpoint', type=float)
  def set_level(self, session, params):
      if params['mode'] == 'voltage' and params['setpoint'] > 24.:
          raise ocs_agent.ParamError("Setpoint must be <= 24 in 'voltage' mode.")
      if params['mode'] == 'current' ad params['setpoint'] > 2.:
          raise ocs_agent.ParamError("Setpoint must be <= 2 in 'current' mode.")

Prior to the introduction of ``@params`` and ``ParamError`` in OCS,
params needed to be checked individually, and failures propagated back
manually.  For example::

  def delay_task(self, session, params):
      try:
          delay = float(params.get('delay', 5))
      except ValueError:
          return False, "Invalid value for parameter 'delay'"

