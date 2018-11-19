from ocs import ocs_agent
import time

from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep

import threading

class MyHardwareDevice:

    """
    This example demonstrates the differences between non-blocking
    (reactor thread) and blocking (worker thread) Task
    implementations.
    """

    def task1(self, session, params=None):
        """
        TASK (blocking)

        In a blocking implementation of a Task or Process function, we
        may:

        - perform any blocking I/O operations using standard python
          functions, and use time.sleep.
        - request that twisted operations be scheduled to run in the
          reactor thread (this is done, implicitly, in
          session.post_message).

        We may not:
        - use any twisted facilities, except those specifically
          designated for use in a worker thread (e.g. callFromThread).

        Blocking Operation functions require no special decoration.
        """        
        for step in range(5):
            session.post_message('task1-blocking step %i' % step)
            time.sleep(1)

        return True, 'task1-blocking complete.'

    @inlineCallbacks
    def task2(self, session, params=None):
        """
        TASK (non-blocking)

        In a non-blocking implementation of a Task or Process
        function, we may:

        - use twisted functions freely, as we are running in the
          reactor thread.
        - make blocking i/o requests by wrapping them in
          deferToThread.

        We may not:

        - cause the function to block or sleep using non-twisted
          methods.
        
        Within twisted, asynchronous routines that perform blocking
        operations (without blocking the reactor thread) will return a
        Deferred object, immediately, instead of the result of the
        request you have made.  To suspend the function until the
        actual result is ready, you should:
        - decorate the function with @inlineCallbacks.
        - use the idiom "x = yield Function(...)" idiom.

        This latter idiom is used on the dsleep function; not because
        we care what the function returned but because we definitely
        want to wait until that function has completed before
        proceeding with the next step in our operation.
        """
        for step in range(5):
            session.add_message('task2-nonblocking step %i' % step)
            yield dsleep(1)

        return True, 'task-2 nonblocking complete.'


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.example1')

    my_hd = MyHardwareDevice()
    agent.register_task('task1', my_hd.task1)
    agent.register_task('task2', my_hd.task2, blocking=False)

    runner.run(agent, auto_reconnect=True)
