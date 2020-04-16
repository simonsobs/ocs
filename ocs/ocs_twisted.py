import threading
from contextlib import contextmanager


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
