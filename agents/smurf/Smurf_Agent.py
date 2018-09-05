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

        print("Hardware Initialized")

        # Monitors smurf variables for change
        def listener(var, value, disp):
            print("{} has been updated: {}".format(var, disp))

        self.base.FpgaTopLevel.AppTop.AppCore.StreamControl.StreamCounter.addListener(listener)
        self.base.FpgaTopLevel.AppTop.AppCore.StreamControl.EofeCounter.addListener(listener)
        self.base.FpgaTopLevel.AppTop.AppCore.StreamControl.enable.addListener(listener)

    def enable_streaming(self, session, params=None):
        self.base.FpgaTopLevel.AppTop.AppCore.StreamControl.enable.set(True, write=True)

    def disable_streaming(self, session, params=None):
        self.base.FpgaTopLevel.AppTop.AppCore.StreamControl.enable.set(False, write=True)


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.smurf')

    smurf = Smurf_Agent(agent)
    
    agent.register_task('init', smurf.init_hardware)
    agent.register_task('enable_streaming', smurf.enable_streaming)
    agent.register_task('disable_streaming', smurf.disable_streaming)

    runner.run(agent, auto_reconnect=True)
