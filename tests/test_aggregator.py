import os
import time
import pytest

from unittest.mock import patch

import so3g
from spt3g import core

from ocs.agents.aggregator.drivers import Provider, g3_cast, make_filename


def test_passing_float_in_provider_to_frame():
    """Float is the expected type we should be passing.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': [2]},
                     }
            }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)


def test_passing_float_like_str_in_provider_to_frame():
    """Here we test passing a string amongst ints. This shouldn't make it to
    the aggregator, and instead the Aggregator logs should display an error
    message with the type passed.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1, 2],
                              'key2': ['1', 2]},
                     }
            }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)


def test_passing_non_float_like_str_in_provider_to_frame():
    """Similar to passing a float like str, here we test passing a non-float
    like str. We can't put this into an so3g.IrregBlockDouble(), so this'll fail.
    We raise a TypeError when this happens and describe the type of the passed in
    data.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)


def test_sparsely_sampled_block():
    """If a block is sparsely sampled and published, the aggregator was
    including its block_name anyway, even when missing. This test publishes two
    blocks, writes to_frame, then publishes only one block then checks to makes
    sure the blocks and block_names arrays are of the same length. Lastly, we
    check that the block_name returns when we again save the sparse block.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key3': [0],
                              'key4': ['z']},
                     }
            }
    provider.save_to_block(data)
    data = {'test2': {'block_name': 'test2',
                      'timestamps': [time.time()],
                      'data': {'key1': [1],
                               'key2': ['a']},
                      }
            }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess, clear=True)

    # Now omit the 'test' block.
    provider.frame_start_time = time.time()
    data = {'test2': {'block_name': 'test2',
                      'timestamps': [time.time()],
                      'data': {'key1': [1],
                               'key2': ['a']},
                      }
            }
    provider.save_to_block(data)

    b = provider.to_frame(hksess=sess, clear=True)

    assert len(b['block_names']) == len(b['blocks'])

    # Check the name is present if we again publish 'test'
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key3': [0],
                              'key4': ['z']},
                     }
            }
    provider.save_to_block(data)
    data = {'test2': {'block_name': 'test2',
                      'timestamps': [time.time()],
                      'data': {'key1': [1],
                               'key2': ['a']},
                      }
            }
    provider.save_to_block(data)

    c = provider.to_frame(hksess=sess, clear=True)

    assert len(c['block_names']) == len(c['blocks'])
    assert 'test' in c['block_names']
    assert 'test2' in c['block_names']


# This is perhaps another problem, I'm passing irregular length data sets and
# it's not raising any sort of alarm. How does this get handled?
def test_data_type_in_provider_save_to_block():
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': ['1', 1]},
                     }
            }
    provider.save_to_block(data)


# 'data' field names
def test_passing_invalid_data_field_name1():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    The aggregator will catch the error, but remove invalid characters from the
    string.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'invalid.key': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert 'invalidkey' in provider.blocks['test'].data.keys()
    assert 'invalid.key' not in provider.blocks['test'].data.keys()


def test_passing_invalid_data_field_name2():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    The aggregator will catch the error, but remove invalid characters from the
    string.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'__123invalid.key': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert '__invalidkey' in provider.blocks['test'].data.keys()
    assert '__123invalid.key' not in provider.blocks['test'].data.keys()


def test_passing_too_long_data_field_name():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    The aggregator will catch the error, but remove invalid characters from the
    string.

    This tests passing too long of a field name, which should get truncated.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'a' * 1000: [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert 'a' * 255 in provider.blocks['test'].data.keys()


def test_long_duplicate_name():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    The aggregator will catch the error, but remove invalid characters from the
    string.

    This tests passing two long and eventually duplicated names.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'a' * 1000: [1],
                              'a' * 1001: ['a']},
                     }
            }
    provider.save_to_block(data)

    assert 'a' * 255 in provider.blocks['test'].data.keys()
    assert 'a' * 252 + '_01' in provider.blocks['test'].data.keys()


def test_reducing_to_duplicate_field_names():
    """Invalid data field names get modified by the Aggregator to comply with
    the set rules. This can result in duplicate field names under certain
    conditions.

    This tests passing two invalid field names, which might naively get
    modified to be identical.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'an.invalid.key#': [1],
                              'an.invalid.key%': ['a']},
                     }
            }
    provider.save_to_block(data)

    # Should still be two keys, i.e. one didn't overwrite the other
    assert len(provider.blocks['test'].data.keys()) == 2

    # More specifically, they should be these keys
    assert 'aninvalidkey' in provider.blocks['test'].data.keys()
    assert 'aninvalidkey_01' in provider.blocks['test'].data.keys()


def test_space_replacement_in_field_names():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    Spaces should be replaced by underscores.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'_an invalid key': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert '_an_invalid_key' in provider.blocks['test'].data.keys()
    assert 'key2' in provider.blocks['test'].data.keys()


def test_empty_field_name():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    A blank string should be invalid.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert '' not in provider.blocks['test'].data.keys()


def test_enforced_field_which_becomes_empty():
    """Invalid data field names should get caught by the Feed, however, we
    check for them in the Aggregator as well.

    A totally invalid field will have all characters stripped from it, which is
    again an invalid field.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'123': [1],
                              'key2': ['a']},
                     }
            }
    provider.save_to_block(data)

    assert '' not in provider.blocks['test'].data.keys()
    assert 'invalid_field_123' in provider.blocks['test'].data.keys()


def test_g3_cast():
    correct_tests = [
        ([1, 2, 3, 4], core.G3VectorInt),
        ([1., 2., 3.], core.G3VectorDouble),
        (["a", "b", "c"], core.G3VectorString),
        ([True, False], core.G3VectorBool),
        (3, core.G3Int),
        ("test", core.G3String),
        (True, core.G3Bool),
    ]
    for x, t in correct_tests:
        assert isinstance(g3_cast(x), t)

    assert isinstance(g3_cast(3, time=True), core.G3Time)
    assert isinstance(g3_cast([1, 2, 3], time=True), core.G3VectorTime)

    incorrect_tests = [
        ['a', 'b', 1, 2], [1, 1.0, 2]
    ]
    for x in incorrect_tests:
        with pytest.raises(TypeError):
            g3_cast(x)


def test_make_filename_directory_creation(tmpdir):
    """make_filename() should be able to create directories to store the .g3
    files in.

    """
    test_dir = os.path.join(tmpdir, 'data')
    fname = make_filename(test_dir)
    # Test we could make the subdir
    os.path.isdir(os.path.basename(fname))


def test_make_filename_directory_creation_no_subdirs(tmpdir):
    """make_filename() should raise a FileNotFoundError if make_subdirs is
    False.

    """
    test_dir = os.path.join(tmpdir, 'data')
    with pytest.raises(FileNotFoundError):
        make_filename(test_dir, make_subdirs=False)


@patch('os.makedirs', side_effect=PermissionError('mocked permission error'))
def test_make_filename_directory_creation_permissions(tmpdir):
    """make_filename() should raise a PermissionError if it runs into one when
    making the directories.

    Here we mock raising the PermissionError on the makedirs call.

    """
    test_dir = os.path.join(tmpdir, 'data')
    with pytest.raises(PermissionError) as e_info:
        make_filename(test_dir)
    assert str(e_info.value) == 'mocked permission error'
