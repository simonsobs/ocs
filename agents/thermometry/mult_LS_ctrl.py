
import ocs
from ocs import client_t

def my_script(app):

    therm_addr = u'observatory.thermometry'
    names = ["LS372A", "LS372B", "LS372C"]
    inits = []
    acqs = []

    for name in names:
        agent_addr = therm_addr + "." + name
        inits.append(client_t.TaskClient(app, agent_addr, 'init'))
        acqs.append(client_t.ProcessClient(app, agent_addr, 'acq'))

    for init in inits:
        yield init.start()

    for init in inits:
        yield init.wait(timeout=10)

    for acq in acqs:
        yield acq.start()
        yield client_t.dsleep(3)


    for acq in acqs:
        yield acq.stop()
        yield acq.wait(timeout=10)

if __name__ == '__main__':
    client_t.run_control_script(my_script)
   
