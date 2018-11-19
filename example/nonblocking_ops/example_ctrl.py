"""
This control client is based on the basic OCS example, but simply
launches the two example tasks in series.
"""

import ocs
from ocs import client_t

def my_script(app, agent_addr):
    print('Entered my_script')

    # Obtain handles to both tasks.
    cw1 = client_t.TaskClient(app, agent_addr, 'task1')
    cw2 = client_t.TaskClient(app, agent_addr, 'task2')
    
    print('Starting first task.')
    d1 = yield cw1.start()
    print(d1)
    x = yield cw1.wait(timeout=20)
    print(x)
    
    print('Starting second task.')
    d2 = yield cw2.start()
    print(d2)
    x = yield cw2.wait(timeout=20)
    print(x)


if __name__ == '__main__':
    client_t.run_control_script(my_script, u'observatory.example1')
