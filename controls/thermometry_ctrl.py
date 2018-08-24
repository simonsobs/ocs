
import ocs
from ocs import client_t

def my_script(app, agent_addr):

    print('Entered control')
    init_task = client_t.TaskClient(app, agent_addr, 'lakeshore')
    acq_proc = client_t.ProcessClient(app, agent_addr, 'acq') 
    
    print('Initializing Lakeshore.')
    d1 = yield init_task.start()
    
    print('Waiting for task to terminate...')
    x = yield init_task.wait(timeout=20)
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
    d1 = yield acq_proc.start()

    sleep_time = 20
    try:
        for i in range(sleep_time):
            print('sleeping for {:d} more seconds'.format(sleep_time - i))
            yield client_t.dsleep(1)
    finally:
        print("Stopping acquisition process")
        yield acq_proc.stop()
        yield acq_proc.wait()

if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.thermometry')
   
