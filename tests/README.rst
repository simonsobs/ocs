=======
Testing
=======

Unit tests for OCS. These are separated into tests for hardware and mock tests
(meaning simulated hardware). While it'd be nice to test on hardware all the
time it likely isn't feasible. For this reason we should mock up the hardware
interfaces for thing we'd like to test so that we can test the code.

These tests are likely the same, except with a fake hardware control class.
Writing tests for hardware during development might be quicker than mocking up
the interface, so we present this separation.

Running the Test Suite
----------------------
Decide whether or not you're testing on actual hardware or just mock hardware,
change to the appropriate directory and run with pytest::

  cd mock/
  pytest

When running on hardware, call only the test you'd like to run. For instance,
to test just the Lakeshore 372::

  cd hardware/
  pytest test_ls372.py
