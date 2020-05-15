import time
import pytest

import so3g

from ocs.agent.aggregator import Provider

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
                     'prefix': ''}
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
                     'prefix': ''}
           }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)

# This is perhaps another problem, I'm passing irregular length data sets and
# it's not raising any sort of alarm. How does this get handled?
def test_data_type_in_provider_save_to_block():
    provider = Provider('test_provider', 'test_sessid', 3, 1)
    provider.frame_start_time = time.time()
    data = {'test': {'block_name': 'test',
                     'timestamps': [time.time()],
                     'data': {'key1': [1],
                              'key2': ['1', 1]},
                     'prefix': ''}
           }
    provider.save_to_block(data)

# 'data' field names
def test_passing_invalid_data_field_name():
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
                     'prefix': ''}
           }
    provider.save_to_block(data)

    # Dummy HKSessionHelper
    sess = so3g.hk.HKSessionHelper(description="testing")
    sess.start_time = time.time()
    sess.session_id = 'test_sessid'

    provider.to_frame(hksess=sess)
