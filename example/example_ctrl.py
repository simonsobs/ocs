import ocs
from ocs import client_t

#  @inlineCallbacks
def my_script(app, agent_addr):

    print('Entered my_script')
    cw1 = client_t.TaskClient(app, agent_addr, 'squids')
    cw2 = client_t.TaskClient(app, agent_addr, 'dets')
    cw3 = client_t.ProcessClient(app, agent_addr, 'acq')
    
    # Start a task; wait for the start to return.
    print('Starting a task.')
    d1 = yield cw1.start()
    print(d1)

    print('Waiting for it to terminate...')
    while True:
        x = yield cw1.wait(timeout=None)
        print(x)
        if x[0] == 0: break
    print(x)

    print('Starting a process.')
    d1 = yield cw3.start()
    print(d1)
    for i in range(5):
        print('sleeping...')
        yield client_t.dsleep(1)

    print('Request process stop.')
    d1 = yield cw3.stop()
    print(d1)
    print('Waiting for it to terminate...')
    x = yield cw3.wait()
    print(x)

if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.dets1')
    
