"""Example of a Control Client implemented using a blocking I/O
backend.  Requires the wampy library, wrapped through
ocs.client_wampy.

Unlike example_ctrl.py, which runs within twisted's asynchronous i/o
framework, this script runs in a fully imperative style.
"""

from ocs.client_wampy import ControlClient
import time

addr = 'ws://localhost:8001/ws'
agent = 'observatory.dets1'

with ControlClient(agent, url=addr) as client:
    print(client.call(agent, 'get_tasks'))
    # Request a task to start.
    print('I will request to start a task...')
    resp = client.request('start', 'squids', {})
    print(resp[1])
    print()
    print('Now I will immediately request a conflicting task...')
    resp = client.request('start', 'dets', {})
    print(resp[1])
    print()
    print(client.request('wait', 'dets', {})[1])
    print()

# You don't have to use a context manager.
client = ControlClient(agent_addr=agent, url=addr)
client.start()
    
while True:
    print('Now I will wait for that task to complete...')
    resp = client.call(agent+'.ops', 'wait', 'squids', {}, timeout=0)
    print(resp[1])
    if resp[0] == 0:
        print('Operation terminated, exiting.')
        break
    time.sleep(1)

client.stop()
