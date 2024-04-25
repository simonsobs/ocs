Tests
=====
We use pytest as our test runner for OCS. To run all of the tests, from within
this ``tests/`` directory, run pytest::

  python3 -m pytest

This will run every test, which includes both unit and integration tests. The
unit tests will run quickly, however the integration test will take some time,
and might require some first time setup.

Test Organization
-----------------
Tests that test the functionality of the core ocs library are kept in the root
of the ``tests/`` directory. They are named identically to the core library
module filenames with a ``test_`` prefix.

Agent unit tests, which import and directly run the Agents during testing, are
kept in ``tests/agents/``. Since the ``ocs/agents/`` directory is not within
the core ocs package, these tests insert their respective Agent paths into the
system path for import.

Finally, integration tests that test the Agents and interaction with them
through Clients are kept in ``tests/integration``.

Unit Tests
----------
The unit tests are built to run quickly and test functionality of individual
parts of the OCS library. These are run automatically on every commit to a
branch/PR on GitHub, using GitHub Actions.  However, you might want to run them
locally when updating or adding to OCS for faster feedback. To run only the
unit tests run::

  python3 -m pytest -m 'not integtest'

This ``-m 'not integtest'`` argument skips all tests marked as integration
tests, leaving just the unit tests.

    *Note:* Unit tests can be run within a Docker container to avoid the
    spt3g/so3g dependencies on the host system. Ensure the ocs Docker image is
    built with your changes, then run::

        $ docker run --rm -w="/app/ocs/tests/" ocs sh -c "python3 -m pytest -m 'not integtest'"

Integration Tests
-----------------
These tests are built to test the running OCS system, and as such need several
running components. This includes a crossbar server and each core OCS Agent. In
order to run these in an isolated environment we make use of Docker and Docker
Compose. This includes use of the pytest plugin, pytest-docker-compose.

For each integration test, a set of Docker containers is started and interacted
with. Startup and shutdown of these containers can increase the testing time.
Additionally, the types of tests this includes generally include checking
behavior after some interactions with the system, which can also take some
time. As such you might be interested in running just a single test that you
are working on. You can do so with::

  python3 -m pytest -k <function name of test you are running>

This should deselect all other tests and run the test of interest. You can run
all integration tests with::

  python3 -m pytest -m integtest

.. note::
    To avoid conflicts with testing on a system already running OCS, containers
    used in testing are named to avoid generic names like 'crossbar' or
    'influxdb'. Also ports have been moved to 'port number + 10000' (i.e.
    crossbar on port 18001 instead of port 8001.)

Reducing Turnaround Time in Testing
```````````````````````````````````
Since the integration tests depend on docker containers you need to have the
docker images built prior to running the tests. You can build all of the docker
images from the root of the ocs repo::

  $ docker compose build

However, if you're making changes to the core of OCS, having to rebuild all
images with every change prior to running the tests quickly becomes time
consuming. To avoid having to do the rebuild, you can mount the local copy of
ocs over the one in the container, located at ``/app/ocs/``. To do this, add a
new volume to the docker compose file in this tests directory for the
Agent/container you are working on. For example, in the fake-data-agent::

  fake-data1:
    image: ocs-fake-data-agent
    container_name: "fake-data-agent"
    hostname: ocs-docker
    environment:
      - LOGLEVEL=debug
    volumes:
      - ./default.yaml:/config/default.yaml:ro
      - /home/user/git/ocs/:/app/ocs/
    command:
      - "--instance-id=fake-data1"
      - "--site-hub=ws://crossbar:18001/ws"
      - "--site-http=http://crossbar:18001/call"

Code Coverage
-------------
Code coverage reports can be produced with the ``--cov`` flag::

  python3 -m pytest -m 'not integtest' --cov

These results are also published to `coveralls`_.

    *Note:* Code coverage for the integration tests is a bit tricky with things
    running in containers, and so is not accurately reflected in these reports.

.. _coveralls: https://coveralls.io/github/simonsobs/ocs
