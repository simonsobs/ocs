from ocs import ocs_agent, site_config, client_t
from ocs.Lakeshore.Lakeshore240 import Module
import random
import time
import threading
from autobahn.wamp.exception import ApplicationError


class LS240_Agent:

    def __init__(self, agent, fake_data = False, port="/dev/ttyUSB0"):
        self.active = True
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()
        self.job = None
        self.fake_data = fake_data
        self.module = None
        self.port = port
        self.thermometers = []
        self.log = agent.log

        self.agent.register_feed('temperatures', agg_params={'aggregate': True})
        self.registered = False

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
    def init_lakeshore_task(self, session, params=None):
        ok, msg = self.try_set_job('init')

        self.log.info('Initialized Lakeshore: {status}', status=ok)
        if not ok:
            return ok, msg

        session.post_status('starting')

        # Registers agent
        try:
            register_t = client_t.TaskClient(session.app, 'observatory.registry', 'register_agent')
            session.call_operation(register_t.start, self.agent.encoded(), block=True)
            self.registered = True
        except ApplicationError as e:
            if e.error == u'wamp.error.no_such_procedure':
                self.log.error("Registry is not running")

        if self.fake_data:
            session.post_message("No initialization since faking data")
            self.thermometers = ["thermA", "thermB"]

        else:
            try:
                self.module = Module(port=self.port)
                print("Initialized Lakeshore module: {!s}".format(self.module))
                session.post_message("Lakeshore initialized with ID: %s"%self.module.inst_sn)

                self.thermometers = [channel._name for channel in self.module.channels]

            except Exception as e:
                print(e)

        self.set_job_done()
        return True, 'Lakeshore module initialized.'

    # Process functions.
    def start_acq(self, session, params=None):
        ok, msg = self.try_set_job('acq')
        if not ok: return ok, msg
        session.post_status('running')

        while True:
            with self.lock:
                if self.job == '!acq':
                    break
                elif self.job == 'acq':
                    pass
                else:
                    return 10

            data = {}

            if self.fake_data:
                for therm in self.thermometers:
                    data[therm] = (time.time(), random.randrange(250, 350))
                time.sleep(.2)

            else:
                for i, channel in enumerate(self.module.channels):
                    data[self.thermometers[i]] = (time.time(), channel.get_reading())

            print("Data: {}".format(data))
            session.app.publish_to_feed('temperatures', data)

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
    parser = site_config.add_arguments()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--serial-number')
    pgroup.add_argument('--mode')
    pgroup.add_argument('--fake-data', action="store_true")

    # Parse comand line.
    args = parser.parse_args()

    # Interpret options in the context of site_config.
    site_config.reparse_args(args, 'Lakeshore240Agent')

    agent, runner = ocs_agent.init_site_agent(args)

    therm = LS240_Agent(agent, fake_data=args.fake_data)

    agent.register_task('init_lakeshore', therm.init_lakeshore_task)
    agent.register_process('acq', therm.start_acq, therm.stop_acq)

    runner.run(agent, auto_reconnect=True)
