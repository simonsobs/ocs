
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):

    agg_addr = "{}.aggregator".format(pargs.address_root)

    therm_addr = "{}.{}".format(pargs.address_root, pargs.target)
    feed_name = 'temperatures'

    print('Entered control')

    print("Registering tasks")
    # Thermometry tasks
    init_ls = client_t.TaskClient(app, therm_addr, 'init_lakeshore')
    get_data = client_t.ProcessClient(app, therm_addr, 'acq')

    # Aggregator tasks
    subscribe = client_t.TaskClient(app, agg_addr, 'subscribe')
    record = client_t.ProcessClient(app, agg_addr, 'record')

    # Start the aggregator running
    #print("Starting Aggregator")

    #params = {'agent_address': therm_addr, 'feed_name': feed_name}
    #yield subscribe.start(params=params)
    #subscribe.wait(timeout=10)

    #agg_params = {
    #    "time_per_file": 60*60,
    #    "time_per_frame": 60*10,
    #    "data_dir": "data/"
    #}
    #yield record.start(params=agg_params)

    #print("Starting Data Acquisition")
    yield init_ls.start()
    yield init_ls.wait(timeout=10)
    #yield get_data.start()

    #sleep_time = 3
    #for i in range(sleep_time):
    #    print('sleeping for {:d} more seconds'.format(sleep_time - i))
    #    yield client_t.dsleep(1)

    #print("Stopping Data Acquisition")
    yield get_data.stop()
    yield get_data.wait()


    #print("Stopping Data Aggregator")
    #yield record.stop()
    #yield record.wait()






if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
