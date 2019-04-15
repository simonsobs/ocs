
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):

    agg_addr = "{}.aggregator".format(pargs.address_root)

    feed_name = 'temperatures'

    print('Entered control')

    print("Registering tasks")
    # Thermometry tasks
    # Aggregator tasks
    subscribe = client_t.TaskClient(app, agg_addr, 'subscribe')
    record = client_t.ProcessClient(app, agg_addr, 'record')

    #print("Stopping Data Aggregator")
    yield record.stop()
    yield record.wait()






if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
