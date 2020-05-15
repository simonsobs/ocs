.. highlight:: python

.. _timeout_lock:

TimeoutLock
============

Overview
---------

In OCS, operations are mainly asynchronous, however most agents have
restrictions on which operations are allowed to be run simultaneously.
For instance, when only one operation can query with a hardware device at a time
through serial communication, and so trying to control hardware variables while
an acquisition process is in progress is dangerous.

In these cases, it is required for agents to create a `lock` which restricts
what operations can run simultaneously. For instance, in your agent it may
be necessary for a process to acquire the lock whenever it talks to the
hardware. Then when a new process is started, it will either grab the lock
if no other operation has it, wait a specified amount of time for the lock
to be free, or fail and return immediately.

The ocs TimeoutLock is a lock that implements a few useful additions to the
standard ``threading.lock``. Mainly:
 -  It can be acquired the ``acquire_timeout`` context
    manager, which will automatically release even if an error is raised.
 -  A ``job`` string can be set on acquisition, so it is clear why an acquisition
    failed.
 -  The ``release_and_acquire`` function can be used to release the lock so that
    so operations can safely run during long-running processes
 -  A ``timeout`` can be set to limit how long an operation will wait for the
    lock before failing.

The following example shows how to acquire the TimeoutLock with the
``acquire_timeout`` context manager::

    lock = TimeoutLock()

    with lock.acquire_timeout(timeout=3.0, job='acq') as acquired:
        if not acquired:
            print(f"Lock could not be acquired because it is held by {lock.job}")
            return False

        print("Lock acquired!")


API
----

.. autoclass:: ocs.ocs_twisted.TimeoutLock
    :members:
