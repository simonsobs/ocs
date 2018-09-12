import threading


class Agent:
    """Generic OCS Agent.

    To be inherited for writing one's own agents.
    """
    def __init__(self):
        self.lock = threading.Semaphore()
        self.job = None

    # Exclusive access management.

    def try_set_job(self, job_name):
        with self.lock:
            if self.job is None:
                self.job = job_name
                return True, 'ok.'
            return False, 'Conflict: "%s" is already running.' % self.job

    def set_job_done(self):
        with self.lock:
            self.job = None


def task(name):
    """Task decorator, apply to function to make an OCS Task.

    Example:
        @task('dets')
        def dets_task(self, session, params=None)
            for det in params[0]:
                session.post_messag(f'Tuning det {det}')
    """
    def real_decorator(function):
        def wrapper(self, session, params):
            # preamble for decorator
            ok, msg = self.try_set_job(name)
            print('start %s:' % name, ok)
            if not ok:
                return ok, msg
            session.post_status('running')

            # function call in decorator
            function(self, session, params)

            # postamble
            self.set_job_done()
            return True, '%s task complete.' % name
        return wrapper
    return real_decorator


def process_start(name):
    """Process Start decorator, apply to function for starting a process."""
    def real_decorator(function):
        def wrapper(self, session, params):
            # preamble for decorator
            ok, msg = self.try_set_job(name)
            print('start %s:' % name, ok)
            if not ok:
                return ok, msg
            session.post_status('running')

            # function call in decorator
            function(self, session, params)

            # postamble
            self.set_job_done()
            return True, '%s task complete.' % name
        return wrapper
    return real_decorator


def process_stop(name):
    """Process Stop function. Use as generic stop process.

    :param name: name of process, must match that given to process_start
    :type name: str

    Example:
        stop_acq = process_stop('acq')
    """
    def real_decorator(self, session, params=None):
        ok = False
        with self.lock:
            if self.job == name:
                self.job = f'!{name}'
                ok = True

        return (ok, {True: 'Requested process stop.',
                     False: 'Failed to request process stop.'}[ok])

    return real_decorator
