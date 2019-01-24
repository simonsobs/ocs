
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):


    root = 'observatory'

    # Register addresses and operations

    agg_instance = 'aggregator'
    agg_address = '{}.{}'.format(root, agg_instance)
    agg_ops = {
        'init': client_t.TaskClient(app, agg_address, 'initialize'),
        'sub':  client_t.TaskClient(app, agg_address, 'subscribe'),
        'agg':  client_t.ProcessClient(app, agg_address, 'aggregate')
    }

    therm_instance = pargs.target
    therm_address = '{}.{}'.format(root, therm_instance)
    therm_ops = {
        'init': client_t.TaskClient(app, therm_address, 'init_lakeshore'),
        'acq': client_t.ProcessClient(app, therm_address, 'acq')
    }

    # Start the aggregator running
    print("Starting Aggregator")

    yield agg_ops['init'].start()
    yield therm_ops['init'].start()

    yield agg_ops['init'].wait()
    yield therm_ops['init'].wait()

    agg_params = {
        "time_per_file": 10 * 60,
        "data_dir": "data/"
    }

    yield agg_ops['agg'].start(params=agg_params)
    yield therm_ops['acq'].start()

    sleep_time = 3
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)

    print("Stopping Data Acquisition")
    yield therm_ops['acq'].stop()
    yield therm_ops['acq'].wait()


    print("Stopping Data Aggregator")
    yield agg_ops['agg'].stop()
    yield agg_ops['agg'].wait()






if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
