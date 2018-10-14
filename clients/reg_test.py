
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):

    reg_address = u'observatory.registry'
    agg_addr = u'observatory.aggregator'
    therm_addr = "{}.{}".format(pargs.address_root, pargs.target)

    # Therm operations
    therm_ops = {
        'init': client_t.TaskClient(app, therm_addr, 'init_lakeshore'),
        'term': client_t.TaskClient(app, therm_addr, 'terminate'),
        'acq': client_t.ProcessClient(app, therm_addr, 'acq')
    }

    agg_ops = {
        'init': client_t.TaskClient(app, agg_addr, 'initialize'),
        'term': client_t.TaskClient(app, agg_addr, 'terminate'),
        'sub':  client_t.TaskClient(app, agg_addr, 'subscribe'),
        'agg':  client_t.ProcessClient(app, agg_addr, 'aggregate')
    }

    yield therm_ops['init'].start()
    yield therm_ops['init'].wait()

    # Initializes Aggregator and Thermometry
    yield agg_ops['init'].start()
    yield agg_ops['init'].wait()


    # Starts data aggregation
    agg_params = {
        "time_per_file": 5,
        "time_per_frame": 10,
        "data_dir": "data2/"
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
    yield therm_ops['term'].start()
    yield therm_ops['term'].wait()


    print("Stopping Data Aggregator")
    yield agg_ops['agg'].stop()
    yield agg_ops['agg'].wait()
    yield agg_ops['term'].start()





if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
