import os

import pytest
import docker

from ocs.testing import check_crossbar_connection


def create_crossbar_fixture():
    # Fixture to wait for crossbar server to be available.
    # Speeds up tests a bit to have this session scoped
    # If tests interfere with eachother change to "function" scoped
    # @pytest.fixture(scope="function")
    @pytest.fixture(scope="session")
    def wait_for_crossbar(docker_services):
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


# Overrides the default location that pytest-docker looks for the compose file.
# https://pypi.org/project/pytest-docker/
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return os.path.join(str(pytestconfig.rootdir), "docker-compose.yml")
