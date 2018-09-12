from ocs import ocs_agent
from ocs.agent import Agent, task, process_start, process_stop

import time


class MyHardwareDevice(Agent):

    def __init__(self):
        # Inherit __init__() from Agent, add any MyHardwareDevice specific
        # attributes below here.
        super(MyHardwareDevice, self).__init__()

    # Task functions.
    @task('squids')
    def squids_task(self, session, params=None):
        for step in range(5):
            session.post_message('Tuning step %i' % step)
            time.sleep(1)

    @task('dets')
    def dets_task(self, session, params=None):
        for i in range(5):
            session.post_message('Dets still tasking...')
            time.sleep(1)

    @process_start('acq')
    def start_acq(self, session, params=None):
        n_frames = 0
        while True:
            with self.lock:
                print('Checking...', self.job)
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10
            n_frames += 100
            time.sleep(.5)
            session.post_message('Acquired %i frames...' % n_frames)

    stop_acq = process_stop('acq')


if __name__ == '__main__':
    agent, runner = ocs_agent.init_ocs_agent('observatory.dets1')

    my_hd = MyHardwareDevice()
    agent.register_task('squids', my_hd.squids_task)
    agent.register_task('dets', my_hd.dets_task)
    agent.register_process('acq', my_hd.start_acq, my_hd.stop_acq)

    runner.run(agent, auto_reconnect=True)
