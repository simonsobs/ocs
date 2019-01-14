"""This is a simple example of an OCS Control Client that runs some
operations on a fake bolometer acquisition system.  The operations are
scripted in the function "my_script".  Note that this script is not a
traditional python function, but instead is a "generator" or
"co-routine".

Clients implemented using ocs.client_t run within an asynchronous
context provided by the twisted library.  Behind the scenes, twisted
runs a single main event loop thread (the "reactor"), and runs our
co-routine, piece by piece, as the things we have requested become
available.  For example, when twisted gets to our request:

  d1 = yield cw1.start()

it issues the a start() request to the specified Task on the remote
Agent, and then suspends the execution of my_script.  The main loop in
twisted proceeds with other jobs it needs to do (for example, to
continue executing other co-routines that might be running at the same
time as ours).  When the response to our "start" request arrives from
the Agent, my_start is resumed with the response from the Agent is
stored in the variable d1.

"""

import ocs
from ocs import client_t

def my_script(app, agent_addr):

    # Instantiate TaskClient and ProcessClient handles for this agent,
    # which we will use to run OCS control commands for each Task and
    # Process.
    
    print('Entered my_script')
    cw1 = client_t.TaskClient(app, agent_addr, 'squids')
    cw2 = client_t.TaskClient(app, agent_addr, 'dets')
    cw3 = client_t.ProcessClient(app, agent_addr, 'acq')
    
    # Start a task; wait for the start command to return.  Note that
    # all requests to the Client handles must be made
    # asynchronously... that means using "yield".  If you don't use
    # "yield", then cw1.start() will return a Twisted "Deferred"
    # object.  And you'll have to read about those.

    print('Starting a task.')
    d1 = yield cw1.start()
    print(d1)

    # The 'wait' operation is exposed by the Agent so that action can
    # be taken upon its completion.  If you pass timeout=None, that
    # disables the timeout function and Agent won't reply until the
    # Operation completes.

    print('Waiting for task to terminate...')
    x = yield cw1.wait(timeout=20)
    print(x)
    if x[0] == ocs.TIMEOUT:
        print('Timeout: the operation did not complete in a timely fashion!')
        return
    elif x[0] != ocs.OK:
        print('Error: the operation exited with error.')
        return
    else:
        print('The task has terminated.')

    # Start a process; then wait for a while.  Note that we cannot use
    # time.sleep to delay, because that will block the twisted main
    # thread from spinning.  instead, use "yield ocs.client_t.dsleep",
    # which will return control to the main thread and then wake this
    # one up when the specified time has elapsed.

    print()
    print('Starting a data acquisition process...')
    d1 = yield cw3.start()
    print(d1)
    for i in range(5):
        print('sleeping...')
        yield client_t.dsleep(1)

    # Unlike tasks, we must explicitly request that a Process be
    # stopped.  Having done so, we should use .wait to confirm it has
    # exited and get the final status.
    print('Request process stop.')
    d1 = yield cw3.stop()
    print(d1)
    print('Waiting for it to terminate...')
    x = yield cw3.wait()
    print(x)

if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.example1')
    
