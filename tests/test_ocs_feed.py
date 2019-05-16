from ocs import ocs_feed


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
