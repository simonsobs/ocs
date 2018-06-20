from ocs import ocs_agent
from ocs.Lakeshore.Lakeshore372 import LS372
from agents.thermometry.LS372_agent import LS372_Agent
import random
import time, threading


names = ["LS372A", "LS372B", "LS372C"]
therms = []

for i, name in enumerate(names):
    agent, runner = ocs_agent.init_ocs_agent('observatory.thermometry.{}'.format(name))
    therms.append(LS372_Agent(name, "0.0.0.0", fake_data=True))
    agent.register_task("init", therms[i].init_lakeshore_task)
    agent.register_process("acq", therms[i].start_acq, therms[i].stop_acq)


    start_reactor = (i == len(names) - 1)
    runner.run(agent, auto_reconnect=True, start_reactor=start_reactor)


