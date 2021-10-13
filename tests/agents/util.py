import pytest
from unittest import mock

from ocs.ocs_agent import OpSession

import txaio
txaio.use_twisted()


def create_agent_fixture(agent_class, agent_kwargs={}):
    """Create a fixture for a given Agent."""

    @pytest.fixture
    def agent():
        mock_agent = mock.MagicMock()
        log = txaio.make_logger()
        txaio.start_logging(level='debug')
        mock_agent.log = log
        log.info('Initialized mock OCSAgent')
        agent_instance = agent_class(mock_agent, **agent_kwargs)

        return agent_instance

    return agent


def create_session(op_name):
    """Create an OpSession with a mocked app for testing."""
    mock_app = mock.MagicMock()
    session = OpSession(1, op_name, app=mock_app)

    return session
