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
        """We should also now be able to pass strings.

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

        test_feed.publish_message(test_message)

    def test_bool_single_sample_input(self):
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                'key1': True,
            }
        }

        with pytest.raises(TypeError):
            test_feed.publish_message(test_message)

    def test_bool_multi_sample_input(self):
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamps': [time.time(), time.time()+1, time.time()+2],
            'data': {
                'key1': [True, False, True],
            }
        }

        with pytest.raises(TypeError):
            test_feed.publish_message(test_message)

    def test_str_multi_sample_input(self):
        """Passing multiple points, including invalid datatypes,
        should cause a TypeError upon publishing.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamps': [time.time(), time.time()+1, time.time()+2],
            'data': {
                'key1': [1., 3.4, 4.3],
                'key2': [10., 'string', None]
            }
        }

        with pytest.raises(TypeError):
            test_feed.publish_message(test_message)

    def test_invalid_data_key_character(self):
        """Passing disallowed characters in a field key should result in a
        ValueError upon publishing.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                'invalid.key1': 1.,
                'valid_key2': 1.,
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_data_key_start_with_number(self):
        """Field names should start with a letter.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '1invalidkey': 1.,
                'valid_key2': 1.,
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_data_key_too_long(self):
        """Passing a data key that exceeds 255 characters should raise a 
        ValueError upon publishing.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                'a'*256: 1.,
                'valid_key2': 1.,
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_data_key_start_underscore1(self):
        """Data keys can start with any number of _'s followed by a letter.
        Test several cases where we start with underscores.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        # Valid underscore + letter start
        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '_valid': 1.,
                'valid_key2': 1.,
            }
        }

        test_feed.publish_message(test_message)

    def test_data_key_start_underscore2(self):
        """Data keys can start with any number of _'s followed by a letter.
        Test several cases where we start with underscores.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        # Valid multi-underscore + letter start
        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '____valid1': 1.,
                'valid_key2': 1.,
            }
        }

        test_feed.publish_message(test_message)

    def test_data_key_start_underscore3(self):
        """Data keys can start with any number of _'s followed by a letter.
        Test several cases where we start with underscores.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        # Invalid underscore + number start
        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '_1valid': 1.,
                'valid_key2': 1.,
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_data_key_start_underscore4(self):
        """Data keys can start with any number of _'s followed by a letter.
        Test several cases where we start with underscores.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        # Invalid multi-underscore + number start
        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '____1valid': 1.,
                'valid_key2': 1.,
            }
        }

        with pytest.raises(ValueError):
            test_feed.publish_message(test_message)

    def test_empty_field_name(self):
        """Check for empty string as a field name.

        """
        mock_agent = MagicMock()
        test_feed = ocs_feed.Feed(mock_agent, 'test_feed', record=True)

        # Invalid multi-underscore + number start
        test_message = {
            'block_name': 'test',
            'timestamp': time.time(),
            'data': {
                '': 1.,
                'valid_key2': 1.,
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
