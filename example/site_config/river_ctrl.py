"""
This example is specifically to demonstrate use of site_config in
a control client.  See other examples to learn about generators and
ocs.client_t in general.
"""

import ocs
from ocs import client_t, site_config

def my_script(app, pargs):

    agent_addr = '%s.%s' % (pargs.address_root, pargs.target)

    print('Entered my_script')
    cw = client_t.ProcessClient(app, agent_addr, 'acq')

    print()
    print('Starting a data acquisition process...')
    d1 = yield cw.start()
    print(d1)
    for i in range(5):
        print('sleeping...')
        yield client_t.dsleep(1)

    print('Request process stop.')
    d1 = yield cw.stop()
    print(d1)
    print('Waiting for it to terminate...')
    x = yield cw.wait()
    print(x)

if __name__ == '__main__':
    parser = site_config.add_arguments()  # initialized ArgParser
    parser.add_argument('--target')          # Options for this client
    client_t.run_control_script2(my_script, parser=parser)
    
