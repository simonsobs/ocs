import os
import time
import yaml

from twisted.internet import reactor, utils, protocol
from twisted.internet.defer import inlineCallbacks


class ManagedInstance(dict):
    """Track properties of a managed Agent-instance.  This is just a dict
    with a schema docstring and an "init" function to set defaults.

    Properties that must be set explicitly by user:

    - 'management' (str): Either 'host', 'docker', or 'retired'.
    - 'agent_class' (str): The agent class name, which may include a
      suffix ([d] or [d?]) if the agent is managed through Docker.
      For instances corresponding to docker services that do not have
      a corresponding SCF entry, the value here will be '[docker]'.
    - 'instance_id' (str): The agent instance-id, or the docker
      service name if the instance is an unmatched docker service.
    - 'full_name' (str): agent_class:instance_id

    Properties that are given a default value by init function:

    - 'operable' (bool): indicates whether the instance can be
      manipulated (whether calls to up/down should be expected to
      work).
    - 'agent_script' (str): Path to the launcher script (if host
      system managed).  If docker-managed, this is the service name.
    - 'prot': The twisted ProcessProtocol object (if host system
      managed), or the DockerContainerHelper (if a docker container).
    - 'target_state' (state): The state we're trying to achieve (up or
      down).
    - 'next_action' (state): The thing HostManager needs to do next;
      this will sometimes indicate the "current state" (up or down),
      but sometimes it will carry a transitional state, such as
      "wait_start".
    - 'at' (float): a unix timestamp for transitional states
      (e.g. used to set how long to wait for something).
    - 'fail_times' (list of floats): unix timestamps when the instance
      process has stopped unexpectedly (used to identify "unstable"
      agents).

    """
    @classmethod
    def init(cls, **kwargs):
        # Note some core things are not included.
        self = cls({
            'agent_script': None,
            'operable': False,
            'prot': None,
            'next_action': 'down',
            'target_state': 'down',
            'fail_times': [],
            'at': 0,
        })
        self.update(kwargs)
        return self


def resolve_child_state(db):
    """Args:

      db (ManagedInstance): the instance state information.  This will
        be modified in place.

    Returns:

      Dict with important actions for caller to take.  Content is:

      - 'messages' (list of str): messages for the session.
      - 'launch' (bool): whether to launch a new instance.
      - 'terminate' (bool): whether to terminate the instance.
      - 'sleep' (float): maximum delay before checking back, or None
        if this machine doesn't care.

    """
    actions = {
        'launch': False,
        'terminate': False,
        'sleep': None,
    }

    messages = []
    sleeps = []

    # State machine.
    prot = db['prot']

    # If the entry is not "operable", send next_action to '?' and
    # don't try to do anything else.

    if not db['operable']:
        db['next_action'] = '?'

    # The uninterruptible transition state(s) are most easily handled
    # in the same way regardless of target state.

    # Transitional: wait_start, which bridges from start -> up.
    elif db['next_action'] == 'wait_start':
        if prot is not None:
            messages.append('Launched {full_name}'.format(**db))
            db['next_action'] = 'up'
        else:
            if time.time() >= db['at']:
                messages.append('Launch not detected for '
                                '{full_name}!  Will retry.'.format(**db))
                db['next_action'] = 'start_at'
                db['at'] = time.time() + 5.

    # Transitional: wait_dead, which bridges from kill -> idle.
    elif db['next_action'] == 'wait_dead':
        if prot is None:
            stat, t = 0, None
        else:
            stat, t = prot.status
        if stat is not None:
            db['next_action'] = 'down'
        elif time.time() >= db['at']:
            if stat is None:
                messages.append('Agent instance {full_name} '
                                'refused to die.'.format(**db))
                db['next_action'] = 'down'
        else:
            sleeps.append(db['at'] - time.time())

    # State handling when target is to be 'up'.
    elif db['target_state'] == 'up':
        if db['next_action'] == 'start_at':
            if time.time() >= db['at']:
                db['next_action'] = 'start'
            else:
                sleeps.append(db['at'] - time.time())
        elif db['next_action'] == 'start':
            messages.append(
                'Requested launch for {full_name}'.format(**db))
            actions['launch'] = True
            db['next_action'] = 'wait_start'
            now = time.time()
            db['at'] = now + 1.
        elif db['next_action'] == 'up':
            if prot is None:
                stat, t = 0, None
            else:
                stat, t = prot.status
            if stat is not None:
                messages.append('Detected exit of {full_name} '
                                'with code {stat}.'.format(stat=stat, **db))
                if hasattr(prot, 'lines'):
                    note = ''
                    lines = prot.lines['stderr']
                    if len(lines) > 50:
                        note = ' (trimmed)'
                        lines = lines[-20:]
                    messages.append('stderr output from {full_name}{note}: {}'
                                    .format('\n'.join(lines), note=note, **db))
                db['next_action'] = 'start_at'
                db['at'] = time.time() + 3
                db['fail_times'].append(time.time())
        else:  # 'down'
            db['next_action'] = 'start'

    # State handling when target is to be 'down'.
    elif db['target_state'] == 'down':
        if db['next_action'] == 'down':
            # The lines below will prevent HostManager from killing
            # Agents that suddenly seem to be alive.  With these
            # lines commented out, someone running "up" on a managed
            # docker-compose.yaml will see their Agents immediately
            # be brought down by HostManager.
            # if prot is not None and prot.status[0] is None:
            #    messages.append('Detected unexpected session for {full_name} '
            #                    '(probably docker); changing target state to "up".'.format(**db))
            #    db['target_state'] = 'up'

            # In fully managed mode, force a termination.
            if prot is not None and prot.status[0] is None:
                messages.append('Detected unexpected session for {full_name} '
                                '(probably docker); it will be shut down.'.format(**db))
                db['next_action'] = 'up'
        elif db['next_action'] == 'up':
            messages.append('Requesting termination of '
                            '{full_name}'.format(**db))
            actions['terminate'] = True
            db['next_action'] = 'wait_dead'
            db['at'] = time.time() + 5
        else:  # 'start_at', 'start'
            messages.append('Modifying state of {full_name} from '
                            '{next_action} to idle'.format(**db))
            db['next_action'] = 'down'

    # Should not get here.
    else:
        messages.append(
            'State machine failure: state={next_action}, target_state'
            '={target_state}'.format(**db))

    actions['messages'] = messages
    if len(sleeps):
        actions['sleep'] = min(sleeps)
    return actions


def stability_factor(times, window=120):
    """Given an increasing list of failure times, quantify the stability
    of the activity.

    A single failure, 10 seconds in the past, has a stability factor
    of 0.5; if there were additional failures before that, the
    stability factor will be lower.

    Returns a culled list of stop times and a stability factor (0 -
    1).

    """
    now = time.time()
    if len(times) == 0:
        return times, 1.
    # Only keep the last few failures, within our time window.
    times = [t for t in times[-200:-1]
             if t >= now - window] + times[-1:]
    dt = [5. / (now - t) for t in times]
    return times, max(1 - sum(dt), 0.)


class AgentProcessHelper(protocol.ProcessProtocol):
    def __init__(self, instance_id, cmd):
        super().__init__()
        self.status = None, None
        self.killed = False
        self.instance_id = instance_id
        self.cmd = cmd
        self.lines = {'stderr': [],
                      'stdout': []}

    def up(self):
        reactor.spawnProcess(self, self.cmd[0], self.cmd[:], env=os.environ)

    def down(self):
        self.killed = True
        # race condition, but it could be worse.
        if self.status[0] is None:
            reactor.callFromThread(self.transport.signalProcess, 'INT')

    # See https://twistedmatrix.com/documents/current/core/howto/process.html
    #
    # These notes, and the useless prototypes below them, are to get
    # us started when we come back here later to feed the process
    # output to high level logging somehow.
    #
    # In a successful launch, we see:
    # - connectionMade (at which point we closeStdin)
    # - inConnectionLost (which is then expected)
    # - childDataReceived(counter, message), output from the script.
    # - later, when process exits: processExited(status).  Status is some
    #   kind of object that knows the return code...
    # In a failed launch, it's the same except note that:
    # - The childDataReceived message contains the python traceback, on,
    #   e.g. realm error.  +1 - Informative.
    # - The processExited(status) knows the return code was not 0.
    #
    # Note that you implement childDataReceived instead of
    # "outReceived" and "errReceived".
    def connectionMade(self):
        self.transport.closeStdin()

    def inConnectionLost(self):
        pass

    def processExited(self, status):
        # print('%s.status:' % self.instance_id, status)
        self.status = status, time.time()

    def outReceived(self, data):
        self.lines['stdout'].extend(data.decode('utf8').split('\n'))
        if len(self.lines['stdout']) > 100:
            self.lines['stdout'] = self.lines['stdout'][-100:]

    def errReceived(self, data):
        self.lines['stderr'].extend(data.decode('utf8').split('\n'))
        if len(self.lines['stderr']) > 100:
            self.lines['stderr'] = self.lines['stderr'][-100:]


def _run_docker(args):
    return utils.getProcessOutputAndValue(
        'docker', args, env=os.environ)


class DockerContainerHelper:
    """Class for managing the docker container associated with some
    service.  Provides some of the same interface as
    AgentProcessHelper.  Pass in a service description dict (such as
    the ones returned by parse_docker_state).

    """

    def __init__(self, service, docker_bin=None):
        self.service = {}
        self.status = -1, time.time()
        self.killed = False
        self.instance_id = service['service']
        self.d = None
        self.update(service)

    def update(self, service):
        """Update self.status based on service info (in format returned by
        parse_docker_state).

        """
        self.service.update(service)
        if service['running']:
            self.status = None, time.time()
        else:
            self.status = service['exit_code'], time.time()
            self.killed = False

    def up(self):
        self.d = _run_docker(
            ['compose', '-f', self.service['compose_file'],
             'up', '-d', self.service['service']])
        self.status = None, time.time()

    def down(self):
        self.d = _run_docker(
            ['compose', '-f', self.service['compose_file'],
             'rm', '--stop', '--force', self.service['service']])
        self.killed = True


@inlineCallbacks
def parse_docker_state(docker_compose_file):
    """Analyze a docker compose.yaml file to get a list of services.
    Using docker compose ps and docker inspect, determine whether each
    service is running or not.

    Returns:
      A dict where the key is the service name and each value is a
      dict with the following entries:

      - 'compose_file': the path to the docker compose file
      - 'service': service name
      - 'container_found': bool, indicates whether a container for
        this service was found (whether or not it was running).
      - 'running': bool, indicating that a container for this service
        is currently in state "Running".
      - 'exit_code': int, which is either extracted from the docker
        inspect output or is set to 127.  (This should never be None.)

    """

    summary = {}

    compose = yaml.safe_load(open(docker_compose_file, 'r'))
    for key, cfg in compose.get('services', []).items():
        summary[key] = {
            'service': key,
            'running': False,
            'exit_code': 127,
            'container_found': False,
            'compose_file': docker_compose_file,
        }

    # Query docker compose for container ids...
    out, err, code = yield _run_docker(
        ['compose', '-f', docker_compose_file, 'ps', '-q'])
    if code != 0:
        raise RuntimeError("Could not run docker compose or could not parse "
                           "compose.yaml file; exit code %i, error text: %s" %
                           (code, err))

    cont_ids = [line.strip() for line in out.decode('utf8').split('\n')
                if line.strip() != '']

    # Run docker inspect.
    for cont_id in cont_ids:
        try:
            info = yield _inspectContainer(cont_id, docker_compose_file)
        except RuntimeError as e:
            print(f'Warning, failed to inspect container {cont_id}; {e}.')
            continue
        if info is None:
            continue

        service = info.pop('service')
        if service not in summary:
            raise RuntimeError("Consistency problem: image does not self-report "
                               "as a listed service? (%s)" % (service))
        summary[service].update(info)

    return summary


@inlineCallbacks
def _inspectContainer(cont_id, docker_compose_file):
    """Run docker inspect on cont_id, return dict with the results."""
    out, err, code = yield _run_docker(
        ['inspect', cont_id])
    if code != 0 and 'No such object' in err.decode('utf8'):
        # This is likely due to a race condition where some
        # container was brought down since we ran docker compose.
        # Return None to indicate this -- caller should just ignore for now.
        print(f'(_inspectContainer: warning, no such object: {cont_id}')
        return None
    elif code != 0:
        raise RuntimeError(
            f'Trouble running "docker inspect {cont_id}".\n'
            f'stdout: {out}\n  stderr {err}')
    # Reconcile config against docker compose ...
    info = yaml.safe_load(out)[0]
    config = info['Config']['Labels']
    _dc_file = os.path.join(config['com.docker.compose.project.working_dir'],
                            config['com.docker.compose.project.config_files'])
    if not os.path.samefile(docker_compose_file, _dc_file):
        raise RuntimeError("Consistency problem: container started from "
                           "some other compose file?\n%s\n%s" % (docker_compose_file, _dc_file))
    service = config['com.docker.compose.service']
    return {
        'service': service,
        'running': info['State']['Running'],
        'exit_code': info['State'].get('ExitCode', 127),
        'container_found': True,
    }
