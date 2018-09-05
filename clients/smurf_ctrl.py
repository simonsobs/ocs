
import ocs
from ocs import client_t

def my_script(app):
    agent_addr = u'observatory.smurf'

    init_hardware = client_t.TaskClient(app, agent_addr, 'init')
    enable_streaming = client_t.TaskClient(app, agent_addr, 'enable_streaming')
    disable_streaming = client_t.TaskClient(app, agent_addr, 'disable_streaming')

    d1 = yield init_hardware.start()
    x = yield init_hardware.wait(timeout=20)

    if x[0] == ocs.TIMEOUT:
        print('Timeout: the operation did not complete in a timely fashion!')
        return
    elif x[0] != ocs.OK:
        print('Error: the operation exited with error.')
        return
    else:
        print('The task has terminated.')
    
    d1 = yield enable_streaming.start()
    x = yield enable_streaming.wait()

    sleep_time = 10

    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)

    d1 = yield disable_streaming.start()
    x = yield disable_streaming.wait()

if __name__ == '__main__':
    client_t.run_control_script(my_script)
   
