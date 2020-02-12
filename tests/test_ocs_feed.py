import time
from unittest.mock import MagicMock

import pytest
from ocs import ocs_feed


# ocs_feed.Feed
class TestPublishMessage:
    """Test ocs_feed.Feed.publish_message().

    """
    def test_valid_single_sample_input(self):
        """We should be able to pass single ints and floats to a feed.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                'key1': 1.,
                'key2': 10,
            }
        }

        test_feed.publish_message(test_message)

    def test_valid_multi_sample_input(self):
        """We should be able to pass lists of ints and floats to a feed.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamps': [time.time(), time.time()+1],
            'data': {
                'key1': [1., 2.],
                'key2': [10, 5]
            }
        }

        test_feed.publish_message(test_message)

    def test_str_single_sample_input(self):
        """Passing a string, even just one, should cause an error upon
        publishing.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                'key1': 1.,
                'key2': 'string',
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_str_multi_sample_input(self):
        """Passing a string, even just one within a list, should cause an error
        upon publishing.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamps': [time.time(), time.time()+1],
            'data': {
                'key1': [1., 3.4],
                'key2': [10., 'string']
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)


# ocs_feed.Block
def test_block_creation():
    """Test the creation of a simple feed Block."""
    test_block = ocs_feed.Block('test_block', ['key1'])
    assert test_block.name == 'test_block'


def test_block_append():
    """Test adding some data to a Block."""
    test_block = ocs_feed.Block('test_block', ['key1'])

    time_samples = [1558044482.2398098, 1558044483.2398098,
                    1558044484.2398098]
    data_samples = [1, 2, 3]

    data = {'timestamp': time_samples,
            'data': {'key1': data_samples}}
    test_block.append(data)

    assert test_block.data['key1'][0] == data_samples
    assert test_block.timestamps[0] == time_samples
