
import ocs
from ocs import client_t

def my_script(app, agent_addr):

    print('Entered control')
    cw1 = client_t.TaskClient(app, agent_addr, 'lakeshore')
    cw2 = client_t.ProcessClient(app, agent_addr, 'acq')
    
    print('Initializing Lakeshore.')
    d1 = yield cw1.start()
    
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
    
        
    print()
    print('Starting a data acquisition process...')
    d1 = yield cw2.start()

    sleep_time = 20
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)


    print('Request process stop.')
    d1 = yield cw2.stop()

    print('Waiting for it to terminate...')
    x = yield cw2.wait()




if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.thermometry')
    
