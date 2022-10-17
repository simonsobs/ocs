import time
import numpy as np
import pytest
from ocs.ocs_twisted import Pacemaker


def test_quantized():
    """
    Tests that Pacemaker forces regular sampling rate when quantize=True.

    """
    sample_freq = 5
    pm = Pacemaker(sample_freq, quantize=True)
    times = []
    for i in range(10):
        pm.sleep()
        print("Sample time: {}".format(time.time()))
        times.append(time.time())
        time.sleep(1 / sample_freq / 3)
    diffs = np.diff(np.array(times))
    # Checks if the diffs (minus the first point due to quantization) match
    tolerance = 1 / sample_freq / 5
    assert np.all(np.abs(diffs - 1 / sample_freq)[1:] < tolerance)


def test_nonquantized():
    """
    Tests that pacemaker forces a regular sample rate when quantize=False.
    In this case, all diffs should be less than the tolerance because
    quantization doesn't mess up the first spacing.
    """
    sample_freq = 5
    pm = Pacemaker(sample_freq, quantize=False)
    times = []
    for _ in range(10):
        pm.sleep()
        print("Sample time: {}".format(time.time()))
        times.append(time.time())
        time.sleep(1 / sample_freq / 3)
    diffs = np.diff(np.array(times))
    # Checks if the diffs (minus the first point due to quantization) match
    tolerance = 1 / sample_freq / 5
    assert np.all(np.abs(diffs - 1 / sample_freq) < tolerance)


def test_non_integer_quantization():
    """
    Trying to quantize with a non-integer sampling frequency should raise an
    error.
    """
    with pytest.raises(ValueError):
        Pacemaker(5.5, quantize=True)
