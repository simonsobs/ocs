from ocs.ocs_twisted import Pacemaker
import time
import numpy as np

def test_pacemaker():
    sample_freq = 5
    pm = Pacemaker(sample_freq, quantize=True)
    times = []
    for i in range(10):
        pm.sleep()
        print("Sample time: {}".format(time.time()))
        times.append(time.time())
        time.sleep(np.random.uniform(0, 1/sample_freq))
    diffs = np.diff(np.array(times))
    # Checks if the diffs (minus the first point due to quantization) match
    assert np.all(np.abs(diffs - 1/sample_freq)[1:] < 1/sample_freq/5)
