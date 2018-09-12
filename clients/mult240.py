
import ocs
from ocs import client_t
import logging


def my_script(app):

    agg_addr = u'observatory.data_aggregator'
    therm_addr = u'observatory.thermometry'


    app.log.error("Registering tasks")
    # Thermometry tasks
    init_modules = client_t.TaskClient(app, therm_addr, 'init_modules')
    get_data = client_t.ProcessClient(app, therm_addr, 'acq')
    # Aggregator tasks
    subscribe = client_t.TaskClient(app, agg_addr, 'subscribe')
    aggregate = client_t.ProcessClient(app, agg_addr, 'aggregate')



    print("Starting Aggregator")
    yield subscribe.start()
    subscribe.wait(timeout=10)
    yield aggregate.start()

    print("Starting Data Acquisition")

    nodes = ["ttyUSB0", "ttyUSB2","ttyUSB3","ttyUSB4"]
    yield init_modules.start(params = {"nodes": nodes})
    yield init_modules.wait(timeout=10)


    # yield get_data.start()

    # sleep_time = 10
    # for i in range(sleep_time):
    #     print('sleeping for {:d} more seconds'.format(sleep_time - i))
    #     yield client_t.dsleep(1)

    # print("Stopping Data Acquisition")
    # yield get_data.stop()
    # yield aggregate.stop()

if __name__ == '__main__':
    client_t.run_control_script(my_script)
   
