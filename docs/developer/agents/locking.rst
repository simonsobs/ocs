.. _timeout_lock:

TimeoutLock
-----------

Overview
^^^^^^^^

In OCS, operations are mainly asynchronous, however most agents have
restrictions on which operations are allowed to be run simultaneously.
For instance, when an Agent interfaces with a hardware device over serial
communication, two commands cannot be issued simultaneously.
In these cases, it may be required for agents to create a `lock` which restricts
what operations can run concurrently.
Requiring this lock to be acquired before any device communication is one
way to ensure that serial messages are not crossed, or avoid any other
dangerous asynchronous behavior.

The ocs :ref:`TimeoutLock <ocs_twisted_api>` is a lock that implements a few useful additions to the
standard ``threading.lock``. Mainly:

- It can be acquired by the ``acquire_timeout`` context
  manager, which will automatically release even if an exception is raised.
- A ``job`` string can be set on acquisition, describing the job obtaining
  the lock.
- The ``release_and_acquire`` function can be used to release the lock so that
  short operations can safely run during long-running processes.
- A ``timeout`` can be set to limit how long an operation will wait for the
  lock before failing.

Examples
^^^^^^^^
acquire_timeout
```````````````
The following example shows how to acquire the TimeoutLock with the
``acquire_timeout`` context manager::

    lock = TimeoutLock()

    with lock.acquire_timeout(timeout=3.0, job='acq') as acquired:
        if not acquired:
            print(f"Lock could not be acquired because it is held by {lock.job}")
            return False
        # Any lock-requiring actions go here
        print("Lock acquired!")


Release and Reacquire
``````````````````````
Here is a slightly more complicated example that shows how an operation might
use the ``release_and_acquire`` function to allow other operations to interject
without completely giving up the lock.

This example shows a simple agent with two operations.
``start_acquisition`` starts a long-running process that can run in a separate
thread that takes the lock and acquires data until ``stop_acquisition`` is run.
``short_action`` is a task that requires the lock, and performs an action that
terminates quickly.
In this case, the acquisition process will release and acquire the lock about
every second, which allows the short action to be run safely without stopping
the acquisition process.
Because the short task acquires the lock with `timeout=3`, it will wait for the
lock for at least 3 seconds, which is long enough that we can be fairly certain
the process will drop the lock::

    class SimpleAgent():
        def __init__(self):
            self.lock = TimeoutLock()

        def short_action(self, session, params=None):
            with self.acquire_timeout(timeout=3, job='short_action') as acquired:
                if not acquired:
                    print(f"Lock could not be acquired because it is held by {self.lock.job}")
                    return False

                # Code that requires lock
                print("Running terminating operation")
                time.sleep(1)

        def start_acquisition(self, session, params=None):
            with self.lock.acquire_timeout(timeout=0, job='acq') as acquired:
                if not acquired:
                    print(f"Lock could not be acquired because it is held by {self.lock.job}")
                    return False

                # Any functionality that requires the lock can go within the
                # ``with`` statement
                last_release = time.time()
                self.run_acq = True
                while self.run_acq:
                    # About every second, release and acquire the lock
                    if time.time() - last_release > 1.:
                        last_release = time.time()
                        if not self.lock.release_and_acquire(timeout=10):
                            print(f"Could not re-acquire lock now held by {self.lock.job}.")
                            return False

                    print("Acquiring Data")
                    time.sleep(0.1)

        def stop_acquisition(self, session, params=None):
            self.run_acq = False

