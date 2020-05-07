import time
import pytest

import so3g
from spt3g import core

from ocs.agent.aggregator import Provider, g3_cast

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
                     'prefix': ''}
           }
    provider.write(data)

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
                     'prefix': ''}
           }
    provider.write(data)

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
                     'prefix': ''}
           }
    provider.write(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)

# This is perhaps another problem, I'm passing irregular length data sets and
# it's not raising any sort of alarm. How does this get handled?
def test_data_type_in_provider_write():
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': ['1', 1]},
                     'prefix': ''}
           }
    provider.write(data)


def test_g3_cast():
    correct_tests = [
        ([1, 2, 3, 4], core.G3VectorInt),
        ([1., 2., 3.], core.G3VectorDouble),
        (["a", "b", "c"], core.G3VectorString),
        (3, core.G3Int),
        ("test", core.G3String)
    ]
    for x, t in correct_tests:
        assert isinstance(g3_cast(x), t)

    assert isinstance(g3_cast(3, time=True), core.G3Time)
    assert isinstance(g3_cast([1, 2, 3], time=True), core.G3VectorTime)

    incorrect_tests = [
        ['a', 'b', 1, 2], True, [1, 1.0, 2]
    ]
    with pytest.raises(TypeError) as e_info:
        for x in incorrect_tests:
            g3_cast(x)
