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
    cw1 = client_t.TaskClient(app, agent_addr, 'subscribe')
    cw2 = client_t.ProcessClient(app, agent_addr, 'aggregate')

    print("Subscribing to Topics")
    d1 = yield cw1.start()

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

    print('Starting a data acquisition process...')
    d1 = yield cw2.start()
    print(d1)

    wait_time = 20
    for i in range(wait_time):
        print('Sleeping for %d more seconds...' %(wait_time - i))
        yield client_t.dsleep(1)

    # Unlike tasks, we must explicitly request that a Process be
    # stopped.  Having done so, we should use .wait to confirm it has
    # exited and get the final status.
    print('Request aggregation stop.')
    d1 = yield cw2.stop()
    print(d1)
    print('Waiting for it to terminate...')
    x = yield cw2.wait()
    print(x)


if __name__ == '__main__':
    # client_t.run_control_script(force_stop, u'observatory.data_aggregator')
    client_t.run_control_script(my_script, u'observatory.data_aggregator')