import pytest
import docker

from ocs.testing import check_crossbar_connection


def create_crossbar_fixture():
    # Fixture to wait for crossbar server to be available.
    # Speeds up tests a bit to have this session scoped
    # If tests start interfering with one another this should be changed to
    # "function" scoped and session_scoped_container_getter should be changed
    # to function_scoped_container_getter
    # @pytest.fixture(scope="session")
    # def wait_for_crossbar(session_scoped_container_getter):
    @pytest.fixture(scope="function")
    def wait_for_crossbar(function_scoped_container_getter):
        """Wait for the crossbar server from docker-compose to become
        responsive.

        """
        check_crossbar_connection()

    return wait_for_crossbar


def restart_crossbar():
    """Restart the crossbar server and wait for it to come back online."""
    client = docker.from_env()
    crossbar_container = client.containers.get('ocs-tests-crossbar')
    crossbar_container.restart()
    check_crossbar_connection()
