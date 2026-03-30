import os
import time
import yaml

from twisted.internet import reactor, utils, protocol
from twisted.internet.defer import inlineCallbacks

from dataclasses import dataclass, field
from typing import List


WAIT_DEAD_TIME = 11
WAIT_START_TIME_INIT = 1
WAIT_START_TIME_FOLLOWUP = 5


@dataclass
class ManagedInstance:
    """Tracks the properties of a managed Agent-instance, including
    how to launch it, the current run state, target state, etc.

    """

    #: How host is managed; either "host", "docker", or "retired".
    management: str

    #: Agent class name (which may include suffix "[d]" or "[d?]" for
    #: docker-managed instances; or simply "[docker]" for services
    #: that do not seem to be registered in the SCF.
    agent_class: str

    #: The agent instance's instance_id, or else the docker service
    #: name associated with entry in the SCF.
    instance_id: str

    #: Indentier constructed as agent_class:instance_id.
    full_name: str

    #: Indicates whether the instance can be manipulated (whether
    #: calls to up/down should be expected to work).
    operable: bool = False

    #: Indicates if instance is retired and can be removed from
    #: tracking.
    retired: bool = False

    #: Indicates if instance should be "passively" managed, e.g. not
    #: be enforced other than ephemerally to attempt a start / stop.
    #: This is expected to only be used for docker-based instances.
    passive_tracking: bool = False

    #: The docker service name, if docker-managed; otherwisre the
    #: string ``__plugin__`` to indicate it is host managed.
    agent_script: str = None

    #: The Twisted ProcessProtocol object, if host system managed; or
    #: else the DockerContainerHelper if docker-based.
    prot: object = None

    #: Indicates a restart is in order, due to change of docker tag or
    #: other new software version.
    restart_required: bool = False

    #: The run state HostManager is trying to enforce (up, down, passive).
    target_state: str = 'down'

    #: The thing HostManager plans to do next; this will sometimes
    #: mirror the current state (up or down) and will sometimes carry a
    #: transitional state, such as "wait_start".
    next_action: str = 'down'

    #: Unix timestamp, used by transitional states to indicate time at
    #: which some subsequent action should be taken.
    at: float = 0

    #: List of unix timestamps for recent events where an instance
    #: stopped unexpectedly; used to identify "unstable" agents.
    fail_times: List = field(default_factory=list)


def resolve_child_state(minst):
    """Args:

      minst (ManagedInstance): the instance state information.  This will
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
    prot = minst.prot

    # If the entry is not "operable", send next_action to '?' and
    # don't try to do anything else.

    if not minst.operable:
        minst.next_action = '?'

    # The uninterruptible transition state(s) are most easily handled
    # in the same way regardless of target state.

    # Transitional: wait_start, which bridges from start -> up.
    elif minst.next_action == 'wait_start':
        if prot is not None:
            messages.append('Launched {0.full_name}'.format(minst))
            minst.next_action = 'up'
            if minst.passive_tracking:
                minst.target_state = 'passive'
        else:
            if time.time() >= minst.at:
                messages.append('Launch not detected for '
                                '{0.full_name}!  Will retry.'.format(minst))
                minst.next_action = 'start_at'
                minst.at = time.time() + WAIT_START_TIME_FOLLOWUP

    # Transitional: wait_dead, which bridges from kill -> idle.
    elif minst.next_action == 'wait_dead':
        if prot is None:
            stat, t = 0, None
        else:
            stat, t = prot.status
        if stat is not None:
            minst.next_action = 'down'
            if minst.passive_tracking:
                minst.target_state = 'passive'
            messages.append('Agent instance {0.full_name} has exited'
                            .format(minst))
        elif time.time() >= minst.at:
            if stat is None:
                messages.append('Agent instance {0.full_name} '
                                'refused to die.'.format(minst))
                minst.next_action = 'down'
        else:
            sleeps.append(minst.at - time.time())

    # State handling when target is to be 'up'.
    elif minst.target_state == 'up':
        if minst.next_action == 'start_at':
            if time.time() >= minst.at:
                minst.next_action = 'start'
            else:
                sleeps.append(minst.at - time.time())
        elif minst.next_action == 'start':
            messages.append(
                'Requested launch for {0.full_name}'.format(minst))
            actions['launch'] = True
            minst.next_action = 'wait_start'
            now = time.time()
            minst.at = now + WAIT_START_TIME_INIT
        elif minst.next_action == 'up':
            if prot is None:
                stat, t = 0, None
            else:
                stat, t = prot.status
            if stat is not None:
                messages.append('Detected exit of {0.full_name} '
                                'with code {stat}.'.format(minst, stat=stat))
                if hasattr(prot, 'lines'):
                    note = ''
                    lines = prot.lines['stderr']
                    if len(lines) > 50:
                        note = ' (trimmed)'
                        lines = lines[-20:]
                    messages.append('stderr output from {minst.full_name}{note}: {}'
                                    .format('\n'.join(lines), note=note, minst=minst))
                minst.next_action = 'start_at'
                minst.at = time.time() + 3
                minst.fail_times.append(time.time())
        else:  # 'down'
            minst.next_action = 'start'

    # State handling when target is to be 'down'.
    elif minst.target_state == 'down':
        if minst.next_action == 'down':
            # The lines below will prevent HostManager from killing
            # Agents that suddenly seem to be alive.  With these
            # lines commented out, someone running "up" on a managed
            # docker-compose.yaml will see their Agents immediately
            # be brought down by HostManager.
            # if prot is not None and prot.status[0] is None:
            #    messages.append('Detected unexpected session for {0.full_name} '
            #                    '(probably docker); changing target state to "up".'.format(minst))
            #    minst.target_state = 'up'

            # In fully managed mode, force a termination.
            if prot is not None and prot.status[0] is None:
                messages.append('Detected unexpected session for {0.full_name} '
                                '(probably docker); it will be shut down.'.format(minst))
                minst.next_action = 'up'
        elif minst.next_action == 'up':
            messages.append('Requesting termination of '
                            '{0.full_name}'.format(minst))
            actions['terminate'] = True
            minst.next_action = 'wait_dead'
            minst.at = time.time() + WAIT_DEAD_TIME
        else:  # 'start_at', 'start'
            messages.append('Modifying state of {0.full_name} from '
                            '{0.next_action} to idle'.format(minst))
            minst.next_action = 'down'

    elif minst.passive_tracking:
        # For passive tracking, next_action always reflects the
        # current running state.
        if prot is None or prot.status[0] is not None:
            minst.next_action = 'down'
        else:
            minst.next_action = 'up'
        minst.target_state = 'passive'

    # Should not get here.
    else:
        messages.append(
            'State machine failure: state={0.next_action}, target_state'
            '={0.target_state}'.format(minst))

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


def _decode(args):
    out, err, code = args
    return (out.decode('utf8'), err.decode('utf8'), code)


def _deyaml(args):
    out, err, code = args
    return (yaml.safe_load(out), err, code)


def _run_docker(args, decode=False, deyaml=False):
    d = utils.getProcessOutputAndValue(
        'docker', args, env=os.environ)
    if decode or deyaml:
        d = d.addCallback(_decode)
    if deyaml:
        d = d.addCallback(_deyaml)
    return d


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
             'up', '--remove-orphans', '-d', self.service['service']])
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
      services:
        A dict where the key is the service name and each value is a
        dict with the following entries:

        - 'compose_file': the path to the docker compose file
        - 'service': service name
        - 'image_tag': the tag listed for the image in the compose
          file (this may differ from the running image).
        - 'image_id': the docker image ID corresponding to
          'image_tag'; will be "unknown" if, e.g., listed tag is not
          yet pulled to the running system.
        - 'container_found': bool, indicates whether a container for
          this service was found (whether or not it was running).
        - 'container_id': the docker ID of the container (if found).
        - 'running': bool, indicating that the found container is
          in state "Running".
        - 'running_image': the ID of the image for the container (if
          found; e.g. "sha:0f...").
        - 'exit_code': int, which is either extracted from the docker
          inspect output or is set to 127. (This should never be None.)

      orphans:
        A dict (by container id) of dicts describing running
        containers that are associated with this compose file but have
        apparently been removed from the service list.  Key is the
        service name.

    """

    summary = {}
    orphans = {}
    compose, err, code = yield _run_docker(['compose', '-f', docker_compose_file, 'config'],
                                           deyaml=True)

    for key, cfg in compose.get('services', {}).items():
        summary[key] = {
            'compose_file': docker_compose_file,
            'service': key,
            'image_tag': cfg['image'],
            'image_id': 'unknown',
            'container_found': False,
            'container_id': None,
            'running': False,
            'running_image': None,
            'exit_code': 127,
        }

    # Look up each tag; create map from tag to image_id.
    to_inspect = list(set([cfg['image_tag'] for cfg in summary.values()]))
    image_ids = {}
    if len(to_inspect):
        # Output from inspect is not neccessarily one-to-one with
        # items on command line, if image of a tag is not yet known.
        out, err, code = yield _run_docker(['inspect'] + to_inspect, deyaml=True)
        for image in out:
            image_ids.update({k: image['Id'] for k in image['RepoTags']})

    for cfg in summary.values():
        cfg['image_id'] = image_ids.get(cfg['image_tag'], 'unknown')

    # Query docker compose for container ids...
    out, err, code = yield _run_docker(
        ['compose', '-f', docker_compose_file, 'ps', '-q'], decode=True)
    if code != 0:
        raise RuntimeError("Could not run docker compose or could not parse "
                           "compose.yaml file; exit code %i, error text: %s" %
                           (code, err))

    cont_ids = [line.strip() for line in out.split('\n')
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
            orphans[cont_id] = {
                'compose_file': docker_compose_file,
                'service': service,
                'container_id': cont_id,
            } | info
        else:
            summary[service].update(info)

    return summary, orphans


@inlineCallbacks
def _inspectContainer(cont_id, docker_compose_file):
    """Run docker inspect on cont_id, return dict with the results."""
    info, err, code = yield _run_docker(
        ['inspect', cont_id], deyaml=True)
    if code != 0 and 'No such object' in err.decode('utf8'):
        # This is likely due to a race condition where some
        # container was brought down since we ran docker compose.
        # Return None to indicate this -- caller should just ignore for now.
        print(f'(_inspectContainer: warning, no such object: {cont_id}')
        return None
    elif code != 0 or len(info) != 1:
        raise RuntimeError(
            f'Trouble running "docker inspect {cont_id}".\n'
            f'stdout: {info}\n  stderr {err}')
    # Reconcile config against docker compose ...
    info = info[0]
    config = info['Config']['Labels']
    _dc_file = os.path.join(config['com.docker.compose.project.working_dir'],
                            config['com.docker.compose.project.config_files'])
    if not os.path.samefile(docker_compose_file, _dc_file):
        raise RuntimeError("Consistency problem: container started from "
                           "some other compose file?\n%s\n%s" % (docker_compose_file, _dc_file))
    service = config['com.docker.compose.service']
    # Note returned dict is merged into summary output for
    # parse_docker_state, so use keys documented there.
    return {
        'service': service,
        'running': info['State']['Running'],
        'exit_code': info['State'].get('ExitCode', 127),
        'container_found': True,
        'running_image': info['Image'],
    }
