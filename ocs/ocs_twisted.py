import threading
from contextlib import contextmanager
import time
from autobahn.twisted.util import sleep as dsleep
from twisted.internet.defer import inlineCallbacks


class TimeoutLock:
    def __init__(self, default_timeout=0):
        """
        Locking mechanism to be used by OCS Agents.

        Args:
            default_timeout (float, optional):
                Sets the default timeout value for acquire calls.
                Defaults to 0.
        """
        self.job = None
        self._active = threading.Lock()
        self._next = threading.Lock()
        self._default_timeout = default_timeout

    def acquire(self, timeout=None, job=None):
        """
        Acquires main lock.

        Args:
            timeout (float, optional):
                Sets the timeout for lock acquisition.

                If set to 0 the acquire calls will be non-blocking and will
                immediately return the result.

                If set to any value greater than 0, this will block until
                the lock is acquired or the timeout (in seconds) has been
                reached.

                If set to -1 this call will block indefinitely until the lock
                has been acquired.

                If not set (default), it will use the TimeoutLock's
                default_value (which itself defaults to 0).

            job (string, optional):
                Job name to be associated with current lock acquisition.
                The current job is stored in self.job so that it can be
                inspected by other threads.

        Returns:
            result (bool): Whether or not lock acquisition was successful.
        """
        if timeout is None:
            timeout = self._default_timeout
        if timeout is None or timeout == 0.:
            kw = {'blocking': False}
        else:
            kw = {'blocking': True, 'timeout': timeout}
        result = False
        if self._next.acquire(**kw):
            if self._active.acquire(**kw):
                self.job = job
                result = True
            self._next.release()
        return result

    def release(self):
        """
        Releases an acquired lock.
        """
        self.job = None
        self._active.release()

    def release_and_acquire(self, timeout=None):
        """
        Releases and immediately reacquires a lock. Because this uses a two-lock
        system, it is guaranteed that at least one  blocking acquire call will
        be able to take the active lock before this function is able to
        re-acquire it. However no other ordering is guaranteed.
        """
        job = self.job
        self.release()
        return self.acquire(timeout=timeout, job=job)

    @contextmanager
    def acquire_timeout(self, timeout=None, job='unnamed'):
        """
        Context manager to acquire and hold a lock.

        Args:
            timeout (float, optional):
                Sets the timeout for lock acquisition. See the ``acquire``
                method documentation for details.

            job (string, optional):
                Job name to be associated with current lock acquisition.

        Returns:
            result (bool): Whether or not lock acquisition was successful.

        The following example will attempt to acquire the lock with a timeout
        of three seconds::

            lock = TimeoutLock()

            with lock.acquire_timeout(timeout=3.0, job='acq') as acquired:
                if not acquired:
                    print(f"Lock could not be acquired because it is held by {lock.job}")
                    return False

                print("Lock acquired!")
        """
        result = self.acquire(timeout=timeout, job=job)
        if result:
            try:
                yield result
            finally:
                self.release()
        else:
            yield result


def in_reactor_context():
    """
    Determine whether the current threading context is the twisted
    main (reactor) thread, or a worker pool thread.  Returns True if
    it's the main thread.  Will raise RuntimeError if the thread name
    is confusing.
    """
    t = threading.currentThread()
    if 'PoolThread' in t.name:
        return False
    if 'MainThread' in t.name:
        return True
    raise RuntimeError('Could not determine threading context: '
                       'currentThread.name="%s"' % t.name)


class Pacemaker:
    """
    The Pacemaker is a class to help Agents maintain a regular sampling rate
    in their processes. The Pacemaker class will correct for the time spent
    in the body of the process loop in it's sleep function. Additionally, if
    run with the ``quantize`` options, the pacemaker will attempt to snap samples
    to a temporal grid (starting on the second) so that different agents can
    remain relatively synchronized.

    Args:
        sample_freq (float):
            The sampling frequency for the pacemaker to enforce. This can be a
            float, however in order to use the ``quantize`` option it must be
            a whole number.
        quantize (bool):
            If True, the pacemaker will snap to a grid starting on the second.
            For instance, if ``sample_freq`` is 4 and ``quantize`` is set to
            True, the pacemaker will make it so samples will land close to
            ``int(second) + (0, 0.25, 0.5, 0.75)``.

    Here is an example of how the Pacemaker can be used keep a 3 Hz quantized
    sample rate::

        pm = Pacemaker(3, quantize=True)
        take_data = True:
        while take_data:
            pm.sleep()
            print("Acquiring thermometry data...")
            time.sleep(np.random.uniform(0, .3))
    """

    def __init__(self, sample_freq, quantize=False):
        self.sample_freq = sample_freq
        self.sample_time = 1. / self.sample_freq
        self.next_sample = time.time()
        self.quantize = quantize

        if quantize and (sample_freq % 1 != 0):
            raise ValueError("Quantization only works for frequencies that are whole numbers.")

    def _set_next_sample(self):
        self.next_sample = time.time() + self.sample_time
        if self.quantize:
            # Snaps "next_sample" to grid defined by sample_freq
            self.next_sample = (self.next_sample + self.sample_time / 2) \
                // self.sample_time * self.sample_time

    def sleep(self):
        """
        Sleeps until the next calculated sampling time.
        """
        now = time.time()
        if now < self.next_sample:
            time.sleep(self.next_sample - now)
        self._set_next_sample()

    @inlineCallbacks
    def dsleep(self):
        """
        Sleeps in a non-blocking way by returning the deferred created by
        twisted's sleep method.
        """
        now = time.time()
        if now < self.next_sample:
            yield dsleep(self.next_sample - now)
        self._set_next_sample()
