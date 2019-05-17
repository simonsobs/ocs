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


def test_block_clear():
    """Test clearing a Block's buffer."""
    test_block = ocs_feed.Block('test_block', ['key1'])

    time_sample = 1558044482.2398098
    data_sample = 1

    data = {'timestamp': time_sample,
            'data': {'key1': data_sample}}
    test_block.append(data)

    assert test_block.data['key1'][0] == data_sample
    test_block.clear()
    assert test_block.empty()

def test_block_append():
    """Test adding some data to a Block."""
    test_block = ocs_feed.Block('test_block', ['key1'])

    time_sample = 1558044482.2398098
    data_sample = 1

    data = {'timestamp': time_sample,
            'data': {'key1': data_sample}}
    test_block.append(data)

    assert test_block.data['key1'][0] == data_sample
    assert test_block.timestamps[0] == time_sample


def test_unmatched_block_append():
    """Test what happens when the data we try to add doesn't match the block
    structure.
    """
    test_block = ocs_feed.Block('test_block', ['key1'])

    time_sample = 1558044482.2398098
    data_sample = 1

    # Note the different 'key2'
    data = {'timestamp': time_sample,
            'data': {'key2': data_sample}}

    with pytest.raises(Exception):
        test_block.append(data)


def test_block_extend():
    """Test extending a Block."""
    test_block1 = ocs_feed.Block('test_block1', ['key1'])
    test_block2 = ocs_feed.Block('test_block2', ['key1'])

    t1 = 1558044482.2398098
    t2 = 1558044483.2398098

    # 1st add some data
    data1 = {'timestamp': t1,
             'data': {'key1': 1}}
    test_block1.append(data1)

    data2 = {'timestamp': t2,
             'data': {'key1': 2}}
    test_block2.append(data2)

    # Now extend block1 with block2
    test_block1.extend(test_block2.encoded())

    assert test_block1.data['key1'] == [1, 2]
    assert test_block1.timestamps == [t1, t2]


def test_unmatched_block_extend():
    """Test extending a Block."""
    test_block1 = ocs_feed.Block('test_block1', ['key1'])
    test_block2 = ocs_feed.Block('test_block2', ['key2'])

    t1 = 1558044482.2398098
    t2 = 1558044483.2398098

    # 1st add some data
    data1 = {'timestamp': t1,
             'data': {'key1': 1}}
    test_block1.append(data1)

    data2 = {'timestamp': t2,
             'data': {'key2': 2}}
    test_block2.append(data2)

    # Now extend block1 with block2
    with pytest.raises(Exception):
        test_block1.extend(test_block2.encoded())


def test_block_encoded():
    """Test a Block is properly encoded."""
    test_block = ocs_feed.Block('test_block', ['key1'])

    time_sample = 1558044482.2398098
    data_sample = 1

    data = {'timestamp': time_sample,
            'data': {'key1': data_sample}}
    test_block.append(data)

    assert test_block.encoded() == {'block_name': 'test_block', 'data': {'key1': [1]}, 'timestamps': [1558044482.2398098]}
