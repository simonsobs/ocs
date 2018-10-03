
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):

    agg_addr = u'observatory.aggregator'

    therm_addr = "{}.{}".format(pargs.address_root, pargs.target)
    data_feed = "{}.data".format(therm_addr)

    print('Entered control')

    print("Registering tasks")
    # Thermometry tasks
    init_ls = client_t.TaskClient(app, therm_addr, 'init_lakeshore')
    get_data = client_t.ProcessClient(app, therm_addr, 'acq')

    # Aggregator tasks
    subscribe = client_t.TaskClient(app, agg_addr, 'subscribe')
    aggregate = client_t.ProcessClient(app, agg_addr, 'aggregate')

    # Start the aggregator running
    print("Starting Aggregator")
    yield subscribe.start(data_feed)
    subscribe.wait(timeout=10)
    yield aggregate.start()

    print("Starting Data Acquisition")
    yield init_ls.start()
    yield init_ls.wait(timeout=10)
    yield get_data.start()

    sleep_time = 3
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)

    print("Stopping Data Acquisition")
    yield get_data.stop()
    yield get_data.wait()


    print("Stopping Data Aggregator")
    yield aggregate.stop()
    yield aggregate.wait()






if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
