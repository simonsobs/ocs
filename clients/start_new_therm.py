
import ocs
from ocs import client_t, site_config


def my_script(app, pargs):
    root = 'observatory'

    # Register addresses and operations
    therm_instance = pargs.target
    therm_address = '{}.{}'.format(root, therm_instance)
    therm_ops = {
        'init': client_t.TaskClient(app, therm_address, 'init_lakeshore'),
        'acq': client_t.ProcessClient(app, therm_address, 'acq')
    }

    yield therm_ops['init'].start()
    yield therm_ops['init'].wait()
    yield client_t.dsleep(.05)

    print("Starting Data Acquisition")
    yield therm_ops['acq'].start()

    #sleep_time = 3
    #for i in range(sleep_time):
    #    print('sleeping for {:d} more seconds'.format(sleep_time - i))
    #    yield client_t.dsleep(1)

    #print("Stopping Data Acquisition")
    #yield therm_ops['acq'].stop()
    #yield therm_ops['acq'].wait()




if __name__ == '__main__':
    parser = site_config.add_arguments()
    parser.add_argument('--target', default="thermo1")
    client_t.run_control_script2(my_script, parser=parser)

   
