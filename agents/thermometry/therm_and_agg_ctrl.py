
import ocs
from ocs import client_t

def my_script(app):

    agg_addr = u'observatory.data_aggregator'
    therm_addr = u'observatory.thermometry'

    print('Entered control')


    print("Registering tasks")
    # Thermometry tasks
    init_ls = client_t.TaskClient(app, therm_addr, 'lakeshore')
    get_data = client_t.ProcessClient(app, therm_addr, 'acq')

    # Aggregator tasks
    subscribe = client_t.TaskClient(app, agg_addr, 'subscribe')
    aggregate = client_t.ProcessClient(app, agg_addr, 'aggregate')

    print("Initializing")
    yield init_ls.start()
    yield subscribe.start()

    yield init_ls.wait(timeout=10)
    yield subscribe.wait(timeout=10)
    print("Finished initialize")

    yield aggregate.start()
    yield get_data.start()


    sleep_time = 10
    for i in range(sleep_time):
        print('sleeping for {:d} more seconds'.format(sleep_time - i))
        yield client_t.dsleep(1)

    yield aggregate.stop()
    yield get_data.stop()

    yield aggregate.wait()
    yield get_data.wait()


if __name__ == '__main__':
    client_t.run_control_script(my_script)
   
