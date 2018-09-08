
import ocs
from ocs import client_t

def my_script(app):
    agent_addr = u'observatory.smurf'

    init_hardware = client_t.TaskClient(app, agent_addr, 'init_hardware')
    read_config = client_t.TaskClient(app, agent_addr, 'read_config')
    set_variable = client_t.TaskClient(app, agent_addr, 'set_variable')
    add_listener = client_t.TaskClient(app, agent_addr, 'add_listener')

    d1 = yield init_hardware.start()
    x = yield init_hardware.wait(timeout=20)
    
    config_filename = '/home/jlashner/dev-board-cryo/Kcu105Eth-0x00000001-20180814145723-mdewart-fb105f10.python/config/defaults.yml'
    yield read_config.start(params={'filename': config_filename})

    def callback(var, value, disp):
        print("Variable {} has been updated to {}".format(var, disp))

    stream_control_path = ['FpgaTopLevel', 'AppTop', 'AppCore', 'StreamControl']
    enable_stream_path = stream_control_path + ['enable']
    stream_counter_path = stream_control_path + ['StreamCounter']



    yield add_listener.start(params={'path': stream_counter_path, 'callback': "test"})
    print("Added Listener")
    yield client_t.dsleep(5)

    print("Disabling streaming")
    yield set_variable.start(params={'path': enable_stream_path, 'value': False})
    yield client_t.dsleep(5)


    print("Enabling streaming")
    yield set_variable.start(params={'path': enable_stream_path, 'value': True})
    yield client_t.dsleep(5)


    print("Disabling streaming")
    yield set_variable.start(params={'path': enable_stream_path, 'value': False})

if __name__ == '__main__':
    client_t.run_control_script(my_script)
   
