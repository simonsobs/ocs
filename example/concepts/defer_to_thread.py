from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks, Deferred

import time

def blockingCalculation(a, b):
    """
    Returns a*b, slowly.  This is an example of a function that
    blocks.  Note that it has no special decorations -- this could
    just as easily be a standard python disk or network function.  But
    time.sleep is enough.
    """
    time.sleep(2.)  # thinking...
    return a*b

def backgroundTick():
    """Print a tick message, and schedule self to re-run regularly."""
    print(' %.1f tick ' % time.time())
    reactor.callLater(0.3, backgroundTick)

@inlineCallbacks
def main():
    """
    Note that this function is decorated with @inlineCallbacks.  This
    is required in order to retrieve the value of a function called
    using "deferToThread".
    """
    print('Start the tick...')
    backgroundTick()

    t0 = time.time()
    print('Method 1 - launch two blocking operations to run concurrently.')
    d1 = threads.deferToThread(blockingCalculation, 6, 7)
    d2 = threads.deferToThread(blockingCalculation, 8, 3)
    v1 = yield d1
    v2 = yield d2
    print('Computed %i and %i in %.2f seconds' % (v1, v2, time.time() - t0))
    
    t0 = time.time()
    print('Method 2 - launch two blocking operations, one after the other.')
    # Get the deferred d1 but then immediately 'yield' on it, to get
    # the return value from the function.
    d1 = threads.deferToThread(blockingCalculation, 6, 7)
    v1 = yield d1
    print('got first result...')
    # This accomplishes the same thing as above, but without bothering
    # to give a name to the deferred (d2).
    v2 = yield threads.deferToThread(blockingCalculation, 8, 3)

    print('Computed %i and %i in %.2f seconds' % (v1, v2, time.time() - t0))
    print('Method 3 - run one computation in reactor thread!')
    print('  This breaks the rules... note how the ticks stop.')
    v1 = blockingCalculation(6, 7)

    print('Done, stopping the reactor.')
    reactor.stop()
    
#Set up "callable" to be run, in the reactor thread, at the next
#opportunity.  Since the reactor is not currently running, the next
#opportunity will be shortly after we call reactor.run().
reactor.callWhenRunning(main)

# Start the reactor.
reactor.run()
