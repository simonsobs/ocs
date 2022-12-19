import time
import pytest
from unittest import mock

from ocs.ocs_agent import OCSAgent, OpSession

import txaio
txaio.use_twisted()


def create_agent_fixture(agent_class, agent_kwargs={}):
    """Create a fixture for a given Agent."""

    @pytest.fixture
    def agent():
        site_args = mock.MagicMock()
        site_args.log_dir = '/tmp/'
        config = mock.MagicMock()
        mock_agent = OCSAgent(config, site_args)

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


def generate_data_for_queue():
    """Just a simple example of data that'll get passed over a feed to the
    aggregator/influxdb publisher.

    """
    data = {'temps': {'block_name': 'test',
                      'data': {'field_0': [1, 2],
                               'field_01': [3, 4]},
                      'timestamps': [time.time(), time.time() + 1]}}
    feed = {'agent_address': 'observatory.test-agent1',
            'agg_params': {'frame_length': 60},
            'feed_name': 'test_feed',
            'address': 'observatory.test-agent1.feeds.test_feed',
            'record': True,
            'session_id': str(time.time())}
    _data = (data, feed)

    return _data
