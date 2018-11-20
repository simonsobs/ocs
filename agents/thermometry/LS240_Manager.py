from ocs import ocs_agent
from ocs.Lakeshore.Lakeshore240 import Module
from ocs.util.getUSBNodes import getUSBNodes
import random
import time
import threading
import os.path

class LS240_Manager:

    def __init__(self, agent):
        self.active = True
        self.log = agent.log
        self.agent = agent
        self.lock = threading.Semaphore()
        self.job = None
        self.modules = {}
        self.thermometers = []

        self.agent_data = {
            'address': agent.agent_address,
        }

    def close(self):
        pass

    # Exclusive access management.
    def try_set_job(self, job_name):
        with self.lock:
            if self.job == None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    # Task functions.
    def init_modules(self, session, params={}):
        """
        Initializes Multiple Lakeshore 240 Modules.
        params:
            - nodes (optional): specifies device ports which you want to connect to
        """
        ok, msg = self.try_set_job('init')
        try:
            nodes = params.get('nodes')
        except: 
            nodes = None


        if nodes is None:
            #Automatically gets all 240 ports using a script. This doesn't work on all operating systems.
            nodes = []
            node_pairs = getUSBNodes()
            for node, product in node_pairs:
                if product == 'Lakeshore240':
                    nodes.append(node)

        for node in nodes:
            self.log.info("Loading Lakeshore 240 from {}".format(node))
            try:
                dev = Module(port = os.path.join('/dev', node), timeout=3)
                self.modules[dev.inst_sn] = dev

                for channel in dev.channels:
                    self.thermometers.append("{}.{}".format(dev.inst_sn, channel._name))
            except TimeoutError:
                self.log.error("Could not load device from {}. Device timed out".format(node))
            except Exception as e:
                print(e)


        self.log.info("Initialized {} Lakeshore modules".format(len(self.modules)))
        self.set_job_done()
        return True, 'Lakeshore module initialized.'

    # Process functions.    

    def start_acq(self, session, params={}):
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.set_status('running')

        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10

            data = {}
            # print('-'*20)
            for (mod_name, module) in self.modules.items():
                for channel in module.channels:
                    therm_name = "{}.{}".format(mod_name, channel._name)
                    data[therm_name] = (time.time(), channel.get_reading())
                    # print("{}: {}".format(therm_name, data[therm_name][1]))


            # self.log.info("Recieved data: {}".format(data))
            session.publish_data(data)

        self.set_job_done()
        return True, 'Acquisition exited cleanly.'

    def stop_acq(self, session, params=None):
        ok = False
        with self.lock:
            if self.job =='acq':
                self.job = '!acq'
                ok = True
        return (ok, {True: 'Requested process stop.',
                     False: 'Failed to request process stop.'}[ok])



if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.thermometry')

    ls_manager = LS240_Manager(agent)
    
    agent.register_task('init_modules', ls_manager.init_modules)
    agent.register_process('acq', ls_manager.start_acq, ls_manager.stop_acq)

    runner.run(agent, auto_reconnect=True)
    ls_manager.close()
