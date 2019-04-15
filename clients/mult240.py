
from ocs import client_t

def my_script(app, pargs):

    root = 'observatory'

    # Register addresses and operations

    agg_instance = 'aggregator'
    agg_address = '{}.{}'.format(root, agg_instance)
    agg_ops = {
        'init': client_t.TaskClient(app, agg_address, 'initialize'),
        'sub':  client_t.TaskClient(app, agg_address, 'add_feed'),
        'agg':  client_t.ProcessClient(app, agg_address, 'record')
    }

    therm_instances = ['thermo1', 'thermo2']
    therm_addresses = {}
    therm_ops = {}
    for t in therm_instances:
        therm_addresses[t] = '{}.{}'.format(root, t)
        therm_ops[t] = {
            'init': client_t.TaskClient(app, therm_addresses[t], 'init_lakeshore'),
            'acq': client_t.ProcessClient(app, therm_addresses[t], 'acq')
        }

    # Init aggregator and thermometry

    yield agg_ops['init'].start()
    for t in therm_instances:
        yield therm_ops[t]['init'].start()

    yield agg_ops['init'].wait()
    for t in therm_instances:
        yield therm_ops[t]['init'].wait()


    # Start Data Acquisition for thermometers
    agg_params = {
        "time_per_file": 60 * 60,
        "data_dir": "data/"
    }
    yield agg_ops['agg'].start(params=agg_params)

    for t in therm_instances:
        yield therm_ops[t]['acq'].start()

    sleep_time = 3
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)

    # Stop Data Acquisition
    print("Stopping Data Acquisition")
    for t in therm_instances:
        yield therm_ops[t]['acq'].stop()
        yield therm_ops[t]['acq'].wait()

    # Stop Aggregator
    print("Stopping Data Aggregator")
    yield agg_ops['agg'].stop()
    yield agg_ops['agg'].wait()


if __name__ == '__main__':
    client_t.run_control_script2(my_script)