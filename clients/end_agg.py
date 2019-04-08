
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
    aggregate = client_t.ProcessClient(app, agg_addr, 'aggregate')

    #print("Stopping Data Aggregator")
    yield aggregate.stop()
    yield aggregate.wait()






if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
