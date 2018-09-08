from ocs import ocs_agent
from ocs.Lakeshore.Lakeshore240 import Module
import random
import time
import threading
import pyrogue as pr
from FpgaTopLevel import *


class Smurf_Agent:

    def __init__(self, agent):
        self.agent = agent
        self.lock = threading.Semaphore()
        self.job = None

        self.args = {
            "simGui": False,
            "commType": "eth-rssi-interleaved",
            "ipAddr": "192.168.2.20",
            "slot": 2,
            "pollEn": True
        }
        self.base = None

    def close(self):
        print("Closing connection")
        if self.base is not None:
            self.base.stop()

    def try_set_job(self, job_name):
        with self.lock:
            if self.job == None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None

    #Init smurf task
    def init_hardware(self, session, params=None):

        self.base = pr.Root(name='AMCc', description='')

        self.base.add(FpgaTopLevel(
            simGui = self.args["simGui"],
            commType = self.args['commType'],
            ipAddr = self.args['ipAddr'],
            pcieRssiLink = (int(self.args['slot']) - 2)
            ))

        streamDataWriter = pr.utilities.fileio.StreamWriter(name="streamDataWriter")
        self.base.add(streamDataWriter)

        pr.streamConnect(self.base.FpgaTopLevel.stream.application(0xC1), self.base.streamDataWriter.getChannel(0))

        self.base.start(pollEn = self.args['pollEn'])

        return True, "Hardware Initialized"

    #Load config file
    def read_config(self, session, params={}):
        """
            Loads configuration file

            params:
                - filename: path to the config file
        """
        filename = params.get("filename")

        if filename is None:
            print("filename must be specified in params. File not loaded.")
            return False, "Correct params not specified"

        self.base.ReadConfig(filename)

        return True, "Loaded config file {}".format(filename)

    def node_from_path(self, path):
        """
            Returns a pyrogue node from a given path.

            params:
                 - path: A list containing the sequence of node names
        """
        cur_node = self.base
        for node in path:
            next_node = cur_node.nodes.get(node)
            if next_node is None:
                raise ValueError("{} has no child {}".format(cur_node.name, node))
            cur_node = next_node

        return cur_node


    def set_variable(self, session, params={}):
        """
            Sets variable
            params:
                - path: Path to the variable in the form of a list of node names
                - value: value to set
                - write: write 
        """
        print(params)
        path  = params.get('path')
        value = params.get('value')
        write = params.get('write', True)

        if path is None or value is None:
            raise ValueError("Must specify path and value in params")

        variable = self.node_from_path(path)
        variable.set(value, write=write)

        return True, "Varibale {} set to {}".format(variable.name, value)

    def add_listener(self, session, params={}):
        """
            Adds listener to a variable
            params:
                - path: Path to the variable in the form of a list of node names
                - callback: Function to be called when variable is updated
                                Callback must have the form: f(var, value, disp)
        """
        path = params.get('path')
        # callback = params.get('callback')
        def callback(var, value, disp):
            print("Variable {} has been updated to {}".format(var, disp))

        if path is None or callback is None:
            raise ValueError("Must specify path and callback in params")

        variable = self.node_from_path(path)
        variable.addListener(callback)

        return True, "Added listener to {}".format(variable.name)


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.smurf')

    smurf = Smurf_Agent(agent)
    
    agent.register_task('init_hardware', smurf.init_hardware)
    agent.register_task('read_config', smurf.read_config)
    agent.register_task('set_variable', smurf.set_variable)
    agent.register_task('add_listener', smurf.add_listener)

    runner.run(agent, auto_reconnect=True)
    smurf.close()
