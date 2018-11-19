import ocs

import txaio
txaio.use_twisted()

from twisted.internet import reactor, task, threads
from twisted.internet.defer import inlineCallbacks, Deferred, DeferredList, FirstError
from twisted.internet.error import ReactorNotRunning

from autobahn.wamp.types import ComponentConfig
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

import time

def init_site_agent(args, address=None):
    """
    Create ApplicationSession and ApplicationRunner instances, set up
    to communicate on the chosen WAMP realm.

    Args:
        args (argparse.Namespace): The arguments, as processed by
            ocs.site_config.

    Returns: (agent, runner).
    """
    if address is None:
        address = '%s.%s' % (args.address_root, args.instance_id)
    server, realm = args.site_hub, args.site_realm
    #txaio.start_logging(level='debug')
    agent = OCSAgent(ComponentConfig(realm, {}), address=address)
    runner = ApplicationRunner(server, realm)
    return agent, runner


def init_ocs_agent(address=None):
    cfg = ocs.get_ocs_config()
    server, realm = cfg.get('default', 'wamp_server'), cfg.get('default', 'wamp_realm')
    #txaio.start_logging(level='debug')
    agent = OCSAgent(ComponentConfig(realm, {}), address=address)
    runner = ApplicationRunner(server, realm)
    return agent, runner


class OCSAgent(ApplicationSession):
    """OCSAgent is used to connect blocking device control code to the
    OCS.  OCSAgent is an ApplicationSession and its methods are all
    run in the twisted main Reactor thread.

    To make use of OCSAgent, the user instantiates it (perhaps through
    init_ocs_agent) with a particular agent_address.  Then the user
    registers task and process functions by calling register_task()
    and register_process().  These are (blocking) functions that will
    be called, in their own twisted thread, when the "start" method is
    request.

    The OCSAgent automatically registers handlers in WAMP, namely:

      {agent_address} - the management_handler function, which
        responds to queries about what tasks and processes are exposed
        by this agent.

      {agent_address}.ops - the device_handler function, which accepts
        Operation commands (start, status, etc.) for all Tasks and
        Processes.

    The OCSAgent also makes use of pubsub channels:

      {agent_address}.feed - a channel to which any session status
        updates are published (written by the Agent; subscribed by any
        interested Control Tools).

    """

    def __init__(self, config, address=None):
        ApplicationSession.__init__(self, config)
        self.tasks = {}       # by op_name
        self.processes = {}   # by op_name
        self.feeds = {}
        self.subscribed_feeds = []
        self.sessions = {}    # by op_name, single OpSession.
        self.next_session_id = 0
        self.session_archive = {} # by op_name, lists of OpSession.
        self.agent_address = address
        self.registered = False
        self.log = txaio.make_logger()

    """
    Methods below are implementations of the ApplicationSession.
    """

    def onConnect(self):
        self.log.info('transport connected')
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        self.log.info('authentication challenge received')

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info('session joined: {}'.format(details))
        # Get an address somehow...
        if self.agent_address is None:
            self.agent_address = 'observatory.random'
        # Register our processes...
        # Register the device interface functions.
        yield self.register(self.my_device_handler, self.agent_address + '.ops')
        yield self.register(self.my_management_handler, self.agent_address)

        self.register_feed("heartbeat", max_messages=1)

        def heartbeat():
            self.publish_to_feed("heartbeat", 0)

        self.heartbeat_call = task.LoopingCall(heartbeat)
        self.heartbeat_call.start(1.0) # Calls the hearbeat every second


    def onLeave(self, details):
        self.log.info('session left: {}'.format(details))
        self.heartbeat_call.stop()

        # Stops all currently running sessions
        for session in self.sessions:
            if self.sessions[session] is not None:
                self.stop(session)

        self.disconnect()

    def onDisconnect(self):
        self.log.info('transport disconnected')
        # this is to clean up stuff. it is not our business to
        # possibly reconnect the underlying connection
        self._countdown = 1
        self._countdown -= 1
        if self._countdown <= 0:
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass

    """The methods below provide OCS framework support."""
            
    def encoded(self):
        """
        Returns a dict describing this Agent.  Includes 'agent_address',
        and lists of 'feeds', 'tasks', and 'processes'.
        """
        return {
            'agent_address': self.agent_address,
            'feeds': [f[1].encoded() for f in self.feeds.items()],
            'tasks': list(self.tasks.keys()),
            'processes': list(self.processes.keys())
        }

    def my_device_handler(self, action, op_name, params=None, timeout=None):
        if action == 'start':
            return self.start(op_name, params=params)
        if action == 'stop':
            return self.stop(op_name, params=params)
        if action == 'wait':
            return self.wait(op_name, timeout=timeout)
        if action == 'status':
            return self.status(op_name)

    def my_management_handler(self, q, **kwargs):
        if q == 'get_tasks':
            result = []
            for k in sorted(self.tasks.keys()):
                session = self.sessions.get(k)
                if session is None:
                    session = {'op_name': k, 'status': 'no_history'}
                else:
                    session = session.encoded()
                result.append((k, session))
            return result
        if q == 'get_processes':
            result = []
            for k in sorted(self.processes.keys()):
                session = self.sessions.get(k)
                if session is None:
                    session = {'op_name': k, 'status': 'no_history'}
                else:
                    session = session.encoded()
                result.append((k, session))
            return result

    def publish_status(self, message, session):
        self.publish(self.agent_address + '.feed', session.encoded())

    def publish_data(self, message, session):
        self.publish(self.agent_address + '.data', session.data_encoded())

    def register_task(self, name, func, blocking=True):
        self.tasks[name] = AgentTask(func, blocking=blocking)
        self.sessions[name] = None

    def register_process(self, name, start_func, stop_func, blocking=True):
        self.processes[name] = AgentProcess(start_func, stop_func,
                                            blocking=blocking)
        self.sessions[name] = None

    def register_feed(self, feed_name, **kwargs):
        """
        Initializes a new feed with name ``feed_name``.

        Args:
            feed_name (string):
                name of the feed
            agg_params (dict, optional):
                Parameters used by the aggregator.
            max_messages (int, optional):
                Max number of messages cached by the feed. Defaults to 20.
        """
        self.feeds[feed_name] = Feed(self, feed_name, **kwargs)

    def publish_to_feed(self, feed_name, message):
        if feed_name not in self.feeds.keys():
            self.log.error("Feed {} is not registered.".format(feed_name))
            return
        self.feeds[feed_name].publish_message(message)

    def subscribe_to_feed(self, agent_addr, feed_name, callback, force_subscribe = False):
        address = "{}.feeds.{}".format(agent_addr, feed_name)

        # Makes sure that feeds are not accidentally subscribed to multiple times if agent is not restarted...
        if address not in self.subscribed_feeds or force_subscribe:
            self.subscribe(callback, address)
            self.subscribed_feeds.append(address)
            return True
        else:
            self.log.error("Feed {} is already subscribed to".format(address))
            return False

    def handle_task_return_val(self, *args, **kw):
        (ok, message), session = args
        session.success = ok
        session.add_message(message)
        session.set_status('done')

    """ The functions below define the OCS API for client control of an
    Agent's Operations.  Some methods are valid on Processs, some on
    Tasks, and some on both."""

    def start(self, op_name, params=None):
        """
        Launch an operation.  Note that successful return of this function
        does not mean that the operation is running; it only means
        that the system has requested the operation to run.

        Returns tuple (status, message, session).

        Possible values for status:

          ocs.ERROR: the specified op_name is not known, or the op is
            already running (has an active session).

          ocs.OK: the Operation start routine has been launched.
        """
        print('start called for %s' % op_name)
        is_task = op_name in self.tasks
        is_proc = op_name in self.processes
        if is_task or is_proc:
            # Confirm it is currently idle.
            session = self.sessions.get(op_name)
            if session is not None:
                if session.status == 'done':
                    # Move to history...
                    #...
                    # Clear from active.
                    self.sessions[op_name] = None
                else:
                    return (ocs.ERROR, 'Operation "%s" already in progress.' % op_name,
                            session.encoded())
            # Mark as started.
            session = OpSession(self.next_session_id, op_name, app=self)
            self.next_session_id += 1
            self.sessions[op_name] = session

            # Get the task/process, prepare to launch.
            if is_task:
                op = self.tasks[op_name]
                msg = 'Started task "%s".' % op_name
            else:
                op = self.processes[op_name]
                msg = 'Started process "%s".' % op_name
                args = (op.launcher, session, params)

            # Launch differently depending on whether op intends to
            # block or not.
            if op.blocking:
                # Launch, soon, in a blockable worker thread.
                session.d = threads.deferToThread(op.launcher, session, params)
            else:
                # Launch, soon, in the main reactor thread.
                session.d = task.deferLater(reactor, 0, op.launcher, session, params)
            session.d.addCallback(self.handle_task_return_val, session)
            return (ocs.OK, msg, session.encoded())
        
        else:
            return (ocs.ERROR, 'No task or process called "%s"' % op_name, {})

    @inlineCallbacks
    def wait(self, op_name, timeout=None):
        """Wait for the specified Operation to become idle, or for timeout
        seconds to elapse.  If timeout==None, the timeout is disabled
        and the function will not return until the Operation
        terminates.  If timeout<=0, then the function will return
        immediately.

        Returns (status, message, session).

        Possible values for status:

          ocs.TIMEOUT: the timeout expired before the Operation became
            idle.

          ocs.ERROR: the specified op_name is not known.

          ocs.OK: the Operation has become idle.

        """
        if not (op_name in self.tasks or op_name in self.processes):
            return (ocs.ERROR, 'Unknown operation "%s".' % op_name, {})
        
        session = self.sessions[op_name]
        if session is None:
            return (ocs.OK, 'Idle.', {})
        ready = True
        if timeout is None:
            results = yield session.d
        elif timeout <= 0:
            ready = bool(session.d.called)
        else:
            # Make a timeout...
            td = Deferred()
            reactor.callLater(timeout, td.callback, None)
            dl = DeferredList([session.d, td], fireOnOneCallback=True,
                              fireOnOneErrback=True, consumeErrors=True)
            try:
                results = yield dl
            except FirstError as e:
                assert e.index == 0  # i.e. session.d raised an error.
                td.cancel()
                e.subFailure.raiseException()
            else:
                if td.called:
                    ready = False
        if ready:
            return (ocs.OK, 'Operation "%s" just exited.' % op_name, session.encoded())
        else:
            return (ocs.TIMEOUT, 'Operation "%s" still running; wait timed out.' % op_name,
                    session.encoded())

    def stop(self, op_name, params=None):
        """
        Launch a Process stop routine.

        Returns (status, message, session).

        Possible values for status:

          ocs.ERROR: the specified op_name is not known, or refers to
            a Task.  Also returned if Process is known but not running.

          ocs.OK: the Process stop routine has been launched.
        """
        if op_name in self.tasks:
            return (ocs.ERROR, 'No implementation for "%s" because it is a task.' % op_name,
                    {})
        elif op_name in self.processes:
            session = self.sessions.get(op_name)
            if session is None:
                return (ocs.ERROR, 'No session active.', {})
            proc = self.processes[op_name]
            d2 = threads.deferToThread(proc.stopper, session, params)
            return (ocs.OK, 'Requested stop on process "%s".' % op_name, session.encoded())
        else:
            return (ocs.ERROR, 'No process called "%s".' % op_name, {})

    def abort(self, op_name, params=None):
        """
        Initiate a Task abort routine.  This function is not currently
        implemented in any useful way.

        Returns (status, message, session).

        Possible values for status:

          ocs.ERROR: you called a function that does not do anything.
        """
        return (ocs.ERROR, 'No implementation for operation "%s"' % op_name, {})

    def status(self, op_name, params=None):
        """
        Get an Operation's session data.

        Returns (status, message, session).  When there is no session
        data available, an empty dictionary is returned instead.

        Possible values for status:

          ocs.ERROR: the specified op_name is not known.

          ocs.OK: the op_name was recognized.
        """
        if op_name in self.tasks or op_name in self.processes:
            session = self.sessions.get(op_name)
            if session is None:
                return (ocs.OK, 'No session active.', {})
            else:
                return (ocs.OK, 'Session active.', session.encoded())
        else:
            return (ocs.ERROR, 'No task or process called "%s"' % op_name, {})


class AgentTask:
    def __init__(self, launcher, blocking=None):
        self.launcher = launcher
        self.blocking = blocking

class AgentProcess:
    def __init__(self, launcher, stopper, blocking=None):
        self.launcher = launcher
        self.stopper = stopper
        self.blocking = blocking

class OpSession:
    """When a caller requests that an Operation (Process or Task) is
    started, an OpSession object is created and is associated with
    that run of the Operation.  The running Operation may update the
    status and post messages to the message buffer.  This is the
    preferred means for communicating Operation status to the caller.

    In the OCSAgent model, Operations run in a separate device thread
    from the main "Reactor".  To maintain data structure integrity,
    code running in the device thread must use post_message() and
    post_status().  In contrast, code running in the main reactor
    thread may use add_message() and add_status().

    The message buffer is purged periodically.
    """
    def __init__(self, session_id, op_name, status='starting', log_status=True,
                 app=None, purge_policy=None):
        self.messages = []  # entries are time-ordered (timestamp, text).
        self.data = None # timestamp, data point
        self.session_id = session_id
        self.op_name = op_name
        self.start_time = time.time()
        self.end_time = None
        self.app = app
        self.success = None

        # This has to be the last call since it depends on init...
        self.set_status(status, log_status=log_status, timestamp=self.start_time)

        # Set up the log message purge.
        self.purge_policy = {
            'min_age_s': 3600,     # Time in seconds after which
                                   # messages can be discarded.
            'min_messages': 5,     # Number of messages to keep,
                                   # even if they have expired.
            'max_messages': 10000, # Max number of messages to keep,
                                   # even if they have not expired.
            }
        if purge_policy is not None:
            self.purge_policy.update(purge_policy)
        self.purge_log()

    def purge_log(self):
        cutoff = time.time() - self.purge_policy['min_age_s']
        while ((len(self.messages) > self.purge_policy['max_messages']) or
               ((len(self.messages) > self.purge_policy['min_messages']) and
                self.messages[0][0] < cutoff)):
            m = self.messages.pop(0)
        # Set this purger to be called again in the future, at some
        # cadence based on the minimum message age.
        next_purge_time = max(self.purge_policy['min_age_s'] / 5, 600)
        self.purger = task.deferLater(reactor, next_purge_time, self.purge_log)

    def encoded(self):
        return {'session_id': self.session_id,
                'op_name': self.op_name,
                'status': self.status,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'success': self.success,
                'messages': self.messages}

    def data_encoded(self):
        return {'data': self.data,
                'op_name': self.op_name,
                'agent_address': self.app.agent_address,
                'session_id': self.session_id}

    def set_status(self, status, timestamp=None, log_status=True):
        assert status in ['starting', 'running', 'stopping', 'done']
        self.status = status
        if timestamp is None:
            timestamp = time.time()
        if status == 'done':
            self.end_time = timestamp
        if log_status:
            self.add_message('Status is now "%s".' % status, timestamp=timestamp)

    def add_message(self, message, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        self.messages.append((timestamp, message))
        self.app.publish_status('Message', self)

    def publish_data(self, message, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        self.data = message
        self.app.publish_data('Message', self)

    # Callable from task / process threads.

    def post_status(self, status):
        reactor.callFromThread(self.set_status, status)
        
    def post_message(self, message):
        reactor.callFromThread(self.add_message, message)

    def post_data(self, data):
        reactor.callFromThread(self.publish_data, data)

    def call_operation(self, operation, params=None, timeout=None, block=False):
        """
        Calls ocs_agent operation.

        Args:
            operation (function):
                operation to call
            params (dict):
                Parameters passed to operation
            timeout (float):
                Operation timeout
            block (bool):
                Whether or not operation should be called in a blocking thread.
        """


        kwargs = {'params': params}
        if timeout is not None:
            kwargs['timeout'] = timeout
        if block:
            return threads.blockingCallFromThread(reactor, operation, **kwargs)
        else:
            reactor.callFromThread(operation, **kwargs)

class Feed:
    """
    Manages publishing to a specific feed and storing of messages.

    Args:
        agent (OCSAgent):
            agent that is registering the feed
        feed_name (string):
            name of the feed
        agg_params (dict, optional):
            Parameters used by the aggregator.
        max_messages (int, optional):
            Max number of messages stored. Defaults to 20.
    """

    def __init__(self, agent, feed_name, agg_params={}, max_messages=20):
        self.messages = []
        self.max_messages = max_messages
        self.agent = agent
        self.agent_address = agent.agent_address
        self.feed_name = feed_name
        self.agg_params = agg_params
        self.address = "{}.feeds.{}".format(self.agent_address, self.feed_name)

    def encoded(self):
        return {
            "agent_address": self.agent_address,
            "feed_name": self.feed_name,
            "address": self.address,
            "messages": self.messages,
            "agg_params": self.agg_params,
        }

    def publish_message(self, message, timestamp = None):
        """
        Publishes message to feed and stores it in ``self.messages``.

        Args:
            message:
                Data to be published
            timestamp (float):
                timestamp given to the message. Defaults to time.time()
        """
        self.agent.publish(self.address,(message, self.encoded()))

        if timestamp is None:
            timestamp = time.time()
        self.messages.append((timestamp, message))
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

