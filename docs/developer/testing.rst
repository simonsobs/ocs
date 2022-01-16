Testing
=======

Writing tests for your OCS Agents is important for the long term maintanence of
your Agent. Tests allow other developers to contribute to your Agent and easily
confirm that their changes did not break functionality within the Agent. With
some setup, tests can also allow you to test your Agent without access to the
hardware that it controls.

Testing within OCS comes in two forms, unit tests and integration tests.  Unit
tests test functionality of the Agent code directly, without running the Agent
itself (or any supporting parts, such as the crossbar server, or a piece of
hardware to connect to.)

Integration tests run a small OCS network, starting up the crossbar server,
your Agent, and any supporting programs that your Agent might need (for
instance, a program accepting serial connections for you Agent to connect to).
As a result, integration tests are more involved than unit tests, requiring
more setup and thus taking longer to execute.

Both types of testing can be important for fully testing the functionality of
your Agent.

Running Tests
-------------

.. include:: ../../tests/README.rst
    :start-line: 2

Testing API
-----------

This section details the helper functions within OCS for assisting with testing
your Agents.

.. automodule:: ocs.testing
    :members:
