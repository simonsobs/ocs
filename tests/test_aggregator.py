import sys
sys.path.insert(0, "../agents/aggregator")

import time
import pytest

import so3g

from aggregator_agent import Provider

def test_passing_float_like_str_in_provider_to_frame():
    """If we pass a string that is float like the aggregator should convert it
    before putting it into the frame. Here we test passing an int and the same int
    as a string. This should pass without error, as the '1' should get
    cast to a float.

    """
    # Dummy Provider for testing
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': ['1']},
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

    This test just makes sure that TypeError is raised.

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

    with pytest.raises(TypeError):
        provider.to_frame(hksess=sess)
