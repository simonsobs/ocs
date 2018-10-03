
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):


    agent_addr = "{}.{}".format(pargs.address_root, pargs.target)

    print('Entered control')
    init_task = client_t.TaskClient(app, agent_addr, 'init_lakeshore')
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

    sleep_time = 3

    for i in range(sleep_time):
        print("Sleeping for {} more seconds".format(sleep_time-i))
        yield client_t.dsleep(1)

    print("Stopping acquisition process")
    yield acq_proc.stop()
    yield acq_proc.wait()


if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)
