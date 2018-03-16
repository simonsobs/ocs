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

    print('Entered my_script')
    sub = client_t.TaskClient(app, agent_addr, 'sub')
    
    print('Subscribing to Thermometry feed.')
    d1 = yield sub.start()
    print(d1)

if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.subscriber')
    
