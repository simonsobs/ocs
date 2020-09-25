import time
import pytest
import urllib.request
from urllib.error import URLError

pytest_plugins = ("docker_compose",)

# Fixture to wait for crossbar server to be available.
@pytest.fixture(scope="function")
def wait_for_crossbar(function_scoped_container_getter):
    """Wait for the crossbar server from docker-compose to become responsive."""
    attempts = 0 

    while attempts < 6:
        try:
            code = urllib.request.urlopen("http://localhost:8001/info").getcode()
        except (URLError, ConnectionResetError):
            print("Crossbar server not online yet, waiting 5 seconds.")
            time.sleep(5)

        attempts += 1

    assert code == 200
    print("Crossbar server online.")

def test_testing(wait_for_crossbar):
    "Just testing if the docker-compose/crossbar wait fixture is working."
    assert True
