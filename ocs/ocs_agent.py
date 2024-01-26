import ocs

import txaio
txaio.use_twisted()

from twisted.application.internet import backoffPolicy
from twisted.internet import reactor, task, threads
from twisted.internet.defer import inlineCallbacks, Deferred, DeferredList, FirstError, maybeDeferred
from twisted.internet.error import ReactorNotRunning

from twisted.python import log
from twisted.logger import formatEvent, FileLogObserver

from autobahn.wamp.types import ComponentConfig, SubscribeOptions
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.twisted.util import sleep as dsleep
from autobahn.wamp.exception import ApplicationError, TransportLost
from autobahn.exception import Disconnected
from .ocs_twisted import in_reactor_context

import json
import math
import time
import datetime
import signal
import socket
import os
from ocs import client_t
from ocs import ocs_feed
from ocs.base import OpCode


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
    # txaio.start_logging(level='debug')
    agent = OCSAgent(ComponentConfig(realm, {}), args, address=address,
                     class_name=getattr(args, 'agent_class', None))
    runner = ApplicationRunner(server, realm)
    return agent, runner


def log_formatter(event):
    text = formatEvent(event)
    t = datetime.datetime.utcnow()
    date_str = t.strftime("%Y-%m-%dT%H-%M-%S.%f")
    return '%s %s\n' % (date_str, text)


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

    def __init__(self, config, site_args, address=None, class_name=None):
        ApplicationSession.__init__(self, config)
        self.log.info("Using OCS version {v}", v=ocs.__version__)
        self.site_args = site_args
        self.tasks = {}       # by op_name
        self.processes = {}   # by op_name
        self.feeds = {}
        self.sessions = {}    # by op_name, single OpSession.
        self.next_session_id = 0
        self.session_archive = {}  # by op_name, lists of OpSession.
        self.agent_address = address
        self.class_name = class_name
        self.registered = False
        self.log = txaio.make_logger()
        self.heartbeat_call = None
        self._heartbeat_on = True
        self.agent_session_id = str(time.time())
        self.startup_ops = []  # list of (op_type, op_name, op_params)
        self.startup_subs = []  # list of dicts with params for subscribe call
        self.subscribed_topics = set()
        self.subscriptions = []  # autobahn.wamp.request.Subscription objects
        self.realm_joined = False
        self.first_time_startup = True

        # Attach the logger.
        log_dir, log_file = site_args.log_dir, None
        if log_dir is not None:
            if not log_dir.startswith('/'):
                if site_args.working_dir is None:
                    self.log.error('Cannot use relative log_dir without '
                                   'explicit working_dir.')
                else:
                    log_dir = os.path.join(site_args.working_dir, log_dir)
            if log_dir is not None and os.path.exists(log_dir):
                log_file = '%s/%s.log' % (log_dir, self.agent_address)
                try:
                    fout = open(log_file, 'a')
                    log.addObserver(FileLogObserver(fout, log_formatter))
                except PermissionError:
                    self.log.error('Permissions error writing to log file %s' % log_file)
            else:
                self.log.error('Log directory does not exist: %s' % log_dir)

        # Can we log already?
        self.log.info('ocs: starting %s @ %s' % (str(self.__class__), address))
        self.log.info('log_file is apparently %s' % (log_file))

    @inlineCallbacks
    def _stop_all_running_sessions(self):
        """Stops all currently running sessions."""
        self.log.info('Stopping all running sessions')
        for session in self.sessions:
            if self.sessions[session] is not None:
                self.log.info("Stopping session {sess}", sess=session)
                self.log.debug("session details: {sess}",
                               sess=self.sessions[session].encoded())
                # Only try to stop starting or running sessions
                if self.sessions[session].status not in ['stopping', 'done']:
                    if session in self.tasks:
                        yield self.abort(session)
                    elif session in self.processes:
                        yield self.stop(session)
        # Give a second for processes to stop cleanly
        yield dsleep(3)

    """
    Methods below are implementations of the ApplicationSession.
    """

    def onConnect(self):
        # Define signal handlers
        @inlineCallbacks
        def signal_handler(sig, frame):
            self.log.info('caught {signal}!', signal=signal.Signals(sig).name)
            yield self._shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.log.info('transport connected')
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        self.log.info('authentication challenge received')

    def _store_subscription(self, subscription, *args, **kwargs):
        self.subscriptions.append(subscription)

    def _unsub_error(self, *args, **kwargs):
        # This just swallows an wamp.error.no_such_subscription exception
        # It is always generated when unsubscribing from stale subscriptions
        pass

    def _unsubscribe_all(self):
        for sub in self.subscriptions:
            self.log.debug('Unsubscribing {sub}', sub=sub)
            try:
                d = sub.unsubscribe()
                d.addErrback(self._unsub_error)
            except Exception as e:
                self.log.error('Error encountered when unsubscribing {sub}:', sub=sub)
                self.log.error('{error}', error=e)

        self.subscriptions = []
        self.subscribed_topics = set()

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info('session joined: {x}', x=details)
        # Get an address somehow...
        if self.agent_address is None:
            self.agent_address = 'observatory.random'
        # Register our processes...
        # Register the device interface functions.
        try:
            yield self.register(self._ops_handler, self.agent_address + '.ops')
            yield self.register(self._management_handler, self.agent_address)
        except ApplicationError as e:
            self.log.error('Failed to register basic handlers!  '
                           'Error: {error}', error=e)
            if e.error == 'wamp.error.not_authorized':
                self.log.error('Are the WAMP realm and OCS address_root consistent '
                               'in OCS site config and crossbar config.json?')
            elif e.error == 'wamp.error.procedure_already_exists':
                self.log.error('Is this agent already running? '
                               'agent_address="{agent_address}"',
                               agent_address=self.agent_address)
            self.leave()
            return

        self.register_feed("heartbeat", max_messages=1)

        def heartbeat():
            if self._heartbeat_on:
                self.log.debug(' {:.1f} {address} heartbeat '
                               .format(time.time(), address=self.agent_address))

                op_codes = {}
                for name, session in self.sessions.items():
                    if session is None:
                        op_codes[name] = OpCode.NONE.value
                    else:
                        op_codes[name] = session.op_code.value
                self.publish_to_feed("heartbeat", op_codes, from_reactor=True)

        self.heartbeat_call = task.LoopingCall(heartbeat)
        self.heartbeat_call.start(1.0)  # Calls the hearbeat every second

        # Remove old subscriptions
        self._unsubscribe_all()

        # Subscribe to startup_subs
        def _subscribe_fail(*args, **kwargs):
            self.log.error('Failed to subscribe to a feed or feed pattern; possible configuration problem.')
            self.log.error(str(args) + str(kwargs))
            self.leave()

        for sub in self.startup_subs:
            d = maybeDeferred(self.subscribe, **sub)
            d.addCallback(self._store_subscription)
            d.addErrback(_subscribe_fail)

        # Now do the startup activities, only the first time we join
        if self.first_time_startup:
            for op_type, op_name, op_params in self.startup_ops:
                self.log.info('startup-op: launching %s' % op_name)
                if op_params is True:
                    op_params = {}
                self.start(op_name, op_params)
            self.first_time_startup = False

        self.realm_joined = True

    @inlineCallbacks
    def onLeave(self, details):
        self.log.info('session left: {}'.format(details))
        if self.heartbeat_call is not None:
            self.heartbeat_call.stop()

        # Normal shutdown
        if details.reason == "wamp.close.normal":
            yield self._stop_all_running_sessions()

        self.disconnect()

        # Unsub from all topics, since we've left the realm
        self.subscribed_topics = set()
        self.realm_joined = False

    @inlineCallbacks
    def _shutdown(self):
        # Stop all sessions and then stop the reactor
        yield self._stop_all_running_sessions()
        try:
            self.log.info('stopping reactor')
            reactor.stop()
        except ReactorNotRunning:
            pass

    @inlineCallbacks
    def onDisconnect(self):
        self.log.info('transport disconnected')
        self.log.info('waiting for reconnection')

        # Wait to see if we reconnect before stopping the reactor
        timeout = self.site_args.crossbar_timeout

        # Wait forever
        if timeout == 0:
            return

        # compute_delay(attempts): Delay in seconds given number of attempts
        # Twisted has an exponential backoff interval that prevents flooding
        # reconnect attempts. We follow that roughly for checking the Agent has
        # reconnected to crossbar up to a 30 second delay.
        compute_delay = backoffPolicy(maxDelay=30.0)

        # Disconnect after timeout
        disconnected_at = time.time()
        attempt = 0
        while time.time() - disconnected_at < timeout:
            attempt += 1  # twisted also starts at 1 attempt

            # successful reconnection
            if self.realm_joined:
                return

            time_left = timeout - (time.time() - disconnected_at)
            self.log.info('waiting at least {} more seconds before giving up'.format(time_left))
            delay = compute_delay(attempt)
            yield dsleep(delay)

        # Shutdown after timeout expires
        yield self._shutdown()

    """The methods below provide OCS framework support."""

    def encoded(self):
        """
        Returns a dict describing this Agent.  Includes 'agent_address',
        and lists of 'feeds', 'tasks', and 'processes'.
        """
        return {
            'agent_address': self.agent_address,
            'session_id': self.agent_session_id,
            'feeds': [f[1].encoded() for f in self.feeds.items()],
            'tasks': list(self.tasks.keys()),
            'processes': list(self.processes.keys())
        }

    def _ops_handler(self, action, op_name, params=None, timeout=None):
        if action == 'start':
            return self.start(op_name, params=params)
        if action == 'stop':
            return self.stop(op_name, params=params)
        if action == 'abort':
            return self.abort(op_name, params=params)
        if action == 'wait':
            return self.wait(op_name, timeout=timeout)
        if action == 'status':
            return self.status(op_name)
        return (ocs.ERROR, 'No implementation for "%s"' % op_name, {})

    def _gather_sessions(self, parent):
        """Gather the session data for self.tasks or self.sessions, for return
        through the management_handler.

        Args:
          parent: either self.tasks or self.processes.

        Returns:

          A list of Operation description tuples, one per registered
          Task or Process.  Each tuple consists of elements `(name,
          session, op_info)`:

          - `name`: The name of the operation.
          - `session`: dict with OpSession.encode(() info for the
            active or most recent session.  If no such session exists
            the result will have member 'status' set to 'no_history'.
          - `op_info`: information registered about the operation,
            such as `op_type`, `docstring` and `blocking`.

        """
        result = []
        for name, op_info in sorted(parent.items()):
            session = self.sessions.get(name)
            if session is None:
                session = {'op_name': name, 'status': 'no_history'}
            else:
                session = session.encoded()
            result.append((name, session, op_info.encoded()))
        return result

    def _management_handler(self, q, **kwargs):
        """Get a description of this Agent's API.  This is for adaptive
        clients (such as MatchedClient) to construct their interfaces.

        Parameters
        ----------
        q : string
          One of 'get_api', 'get_tasks', 'get_processes', 'get_feeds',
          'get_agent_class'.

        Returns
        -------
        api_description : dict
          If the argument is 'get_api', then a dict with the following
          entries is returned:

          - 'agent_class': The class name of this agent.
          - 'instance_hostname': The host name where the Agent is
            running, as returned by socket.gethostname().
          - 'instance_pid': The PID of the Agent interpreter session,
            as returned by os.getpid().
          - 'feeds': The list of encoded feed information, tuples
            (feed_name, feed_info).
          - 'processes': The list of Process api description info, as
            returned by :func:`_gather_sessions`.
          - 'tasks': The list of Task api description info, as
            returned by :func:`_gather_sessions`.

          Passing get_X will, for some values of X, return only that
          subset of the full API; treat that as deprecated.

        """
        if q == 'get_api':
            return {
                'agent_class': self.class_name,
                'instance_hostname': socket.gethostname(),
                'instance_pid': os.getpid(),
                'feeds': [(k, v.encoded()) for k, v in self.feeds.items()],
                'processes': self._gather_sessions(self.processes),
                'tasks': self._gather_sessions(self.tasks),
            }
        if q == 'get_tasks':
            return self._gather_sessions(self.tasks)
        if q == 'get_processes':
            return self._gather_sessions(self.processes)
        if q == 'get_feeds':
            return [(k, v.encoded()) for k, v in self.feeds.items()]
        if q == 'get_agent_class':
            return self.class_name

    def register_task(self, name, func, aborter=None, blocking=True,
                      aborter_blocking=None, startup=False):
        """Register a Task for this agent.

        Args:
            name (string): The name of the Task.
            func (callable): The function that will be called to
                handle the "start" operation of the Task.
            aborter (callable): The function that will be called to
                handle the "abort" operation of the Task (optional).
            blocking (bool): Indicates that ``func`` should be
               launched in a worker thread, rather than running in the
               main reactor thread.
            aborter_blocking(bool or None): Indicates that ``aborter``
               should be run in a worker thread, rather than running
               in the main reactor thread.  Defaults to value of
               ``blocking``.
            startup (bool or dict): Controls if and how the Operation
                is launched when the Agent successfully starts up and
                connects to the WAMP realm.  If False, the Operation
                does not auto-start.  Otherwise, the Operation is
                launched on startup.  If the ``startup`` argument is a
                dictionary, this is passed to the Operation's start
                function.

        Notes:

            The functions func and aborter will be called with
            arguments (session, params) where session is the active
            OpSession and params is passed from the client.

            (Passing params to the aborter might not be supported in
            the client library so don't count on that being useful.)

        """
        self.tasks[name] = AgentTask(
            func, blocking=blocking, aborter=aborter,
            aborter_blocking=aborter_blocking)
        self.sessions[name] = None
        if startup is not False:
            self.startup_ops.append(('task', name, startup))

    def register_process(self, name, start_func, stop_func, blocking=True,
                         stopper_blocking=None, startup=False):
        """Register a Process for this agent.

        Args:
            name (string): The name of the Process.
            start_func (callable): The function that will be called to
                handle the "start" operation of the Process.
            stop_func (callable): The function that will be called to
                handle the "stop" operation of the Process.
            blocking (bool): Indicates that ``start_func`` should be
                launched in a worker thread, rather than running in
                the reactor.
            stopper_blocking (bool or None): Indicates that
                ``stop_func`` should be launched in a worker thread,
                rather than running in the reactor.  Defaults to the
                value of ``blocking``.
            startup (bool or dict): Controls if and how the Operation
                is launched when the Agent successfully starts up and
                connects to the WAMP realm.  If False, the Operation
                does not auto-start.  Otherwise, the Operation is
                launched on startup.  If the ``startup`` argument is a
                dictionary, this is passed to the Operation's start
                function.

        Notes:
            The functions start_func and stop_func will be called with
            arguments (session, params) where session is the active
            OpSession and params is passed from the client.

            (Passing params to the stop_func might not be supported in
            the client library so don't count on that being useful.)

        """
        self.processes[name] = AgentProcess(
            start_func, stop_func, blocking=blocking,
            stopper_blocking=stopper_blocking)
        self.sessions[name] = None
        if startup is not False:
            self.startup_ops.append(('process', name, startup))

    @inlineCallbacks
    def call_op(self, agent_address, op_name, action, params=None, timeout=None):
        """
        Calls ocs_agent operation.

        Args:
            agent_address (string):
                Address of the agent who registered operation
            op_name (string):
                Name of the operation
            action (string):
                Action of operation. start, stop , wait, etc.
            params (dict):
                Params passed to operation
            timeout (float):
                timeout for operation
        """
        if not in_reactor_context():
            x = yield reactor.callFromThread(
                self.call_op, agent_address, op_name, action, params=params, timeout=timeout
            )
            return x

        op = client_t.OperationClient(self, agent_address, op_name)
        try:
            x = yield op.request(action, params=params, timeout=timeout)
            return x
        except ApplicationError as e:
            self.log.warn(e.error)
            if e.error == u'wamp.error.no_such_procedure':
                self.log.warn("Operation {}.ops.{} has not been registered"
                              .format(agent_address, op_name))
            else:
                self.log.warn(e.error)
            return False

    def register_feed(self, feed_name, **kwargs):
        """
        Initializes a new feed with name ``feed_name``.

        Args:
            feed_name (string):
                name of the feed
            record (bool, optional):
                Determines if feed should be aggregated. At the moment, each agent
                can have at most one aggregated feed. Defaults to False
            agg_params (dict, optional):
                Parameters used by the aggregator and influx publisher.  See
                the ``ocs.ocs_feed.Feed`` docstring for the full list of
                aggregator params.
            buffer_time (int, optional):
                Specifies time that messages should be buffered in seconds.
                If 0, message will be published immediately.
                Defaults to 0.
            max_messages (int, optional):
                Max number of messages stored. Defaults to 20.

        Returns:
            The Feed object (which is also cached in self.feeds).
        """
        self.feeds[feed_name] = ocs_feed.Feed(self, feed_name, **kwargs)
        return self.feeds[feed_name]

    def publish_to_feed(self, feed_name, message, from_reactor=None):
        """Publish data to named feed.

        Args:
          feed_name (str): should match the name of a registered feed.
          message (serializable): data to publish.  Acceptable format
            depends on feed configuration; see Feed.publish_message.
          from_reactor (bool or None): This is deprecated; the code
            will check whether you're in a thread or not.

        Notes:
          If an unknown feed_name is passed in, an error is printed to
          the log and that's all.

          If you are running a "blocking" operation, in a thread, then
          it is best if the message is not a persistent data structure
          from your thread (especially something you might modify soon
          after this call).  The code will take a copy of your
          structure and pass that to the reactor thread, but the copy
          may not be deep enough!

        """
        if feed_name not in self.feeds:
            self.log.error("Feed {} is not registered.".format(feed_name))
            return
        # We expect that publish_message will check threading context
        # and do the right thing (as of this writing, it does).
        self.feeds[feed_name].publish_message(message)

    def subscribe(self, handler, topic, options=None, force_subscribe=False):
        """
        Subscribes to a topic for receiving events.
        Identical to ApplicationSession subscribe, but by default prevents
        re-subscription to the same topic multiple times unless
        force_subscribe=True.

        For full documentation see:
        https://autobahn.readthedocs.io/en/latest/reference/autobahn.wamp.html#autobahn.wamp.interfaces.ISession.subscribe

        Args:
            handler (callable):
                handler called with message data
            topic (string):
                uri of topic to subscribe to
            options (dict):
                Dict of subscribe options.
                To set prefix or wildcard matching, set `match` to `prefix`
                or `wildcard` respectively.
                For more info, see https://autobahn.readthedocs.io/en/latest/reference/autobahn.wamp.html#autobahn.wamp.types.SubscribeOptions
            force_subscribe (bool):
                If true, force resubscribe to an already susbscribed topic.
                Defaults to False.
        """
        if (topic not in self.subscribed_topics) or force_subscribe:
            if options is not None:
                options = SubscribeOptions(**options)
            self.subscribed_topics.add(topic)
            return super().subscribe(handler, topic=topic,
                                     options=options)
        else:
            self.log.warn("Topic {} is already subscribed.".format(topic))
            return False

    def subscribe_to_feed(self, agent_addr, feed_name, handler, options=None, force_subscribe=False):
        """
        Constructs topic feed from agent address and feedname, and subscribes to it.

        Args:
            agent_addr (str):
                Full agent address, e.g. `observatory.LS12345`
            feed_name (str):
                Feed name, e.g. `temperatures`
            handler (callable):
                handler called with message data
            options (dict):
                Dict or subscribe options. See https://autobahn.readthedocs.io/en/latest/reference/autobahn.wamp.html#autobahn.wamp.types.SubscribeOptions
            force_subscribe (bool):
                If true, force resubscribe to an already susbscribed topic.
                Defaults to False.
        """
        topic = "{}.feeds.{}".format(agent_addr, feed_name)
        return self.subscribe(handler, topic, options=options, force_subscribe=force_subscribe)

    def subscribe_on_start(self, handler, topic, options=None, force_subscribe=None):
        """
        Schedules a topic to be subscribed to OnJoin.
        See OCSAgent.subscribe's docstring.
        """
        self.startup_subs.append({
            'handler': handler,
            'topic': topic,
            'options': options,
            'force_subscribe': force_subscribe
        })

    def _handle_task_return_val(self, *args, **kw):
        try:
            (ok, message), session = args
            session.add_message(message)
            session.success = ok
            session.set_status('done')
        except BaseException:
            print('Failed to decode _handle_task_return_val args:',
                  args, kw)
            raise

    def _handle_task_error(self, *args, **kw):
        try:
            ex, session = args
            if ex.check(ParamError):
                message = 'ERROR: {}'.format(ex.getErrorMessage())
            else:
                message = 'CRASH: %s' % str(ex)
            session.add_message(message)
            session.success = False
            session.set_status('done')
        except BaseException:
            print('Failure to decode _handle_task_error args:',
                  args, kw)
            raise

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
        print('start called for {}'.format(op_name))
        is_task = op_name in self.tasks
        is_proc = op_name in self.processes
        if is_task or is_proc:
            # Confirm it is currently idle.
            session = self.sessions.get(op_name)
            if session is not None:
                if session.status == 'done':
                    # Move to history...
                    # ...
                    # Clear from active.
                    self.sessions[op_name] = None
                else:
                    return (ocs.ERROR, 'Operation "%s" already in progress.' % op_name,
                            session.encoded())

            # Get the task/process launch function
            if is_task:
                op = self.tasks[op_name]
                msg = 'Started task "%s".' % op_name
            else:
                op = self.processes[op_name]
                msg = 'Started process "%s".' % op_name

            # Pre-process params?
            if hasattr(op.launcher, '_ocs_prescreen'):
                try:
                    handler = ParamHandler(params)
                    params = handler.batch(op.launcher._ocs_prescreen)
                except ParamError as err:
                    self.log.error("Caught ParamError during start call: {err}", err=err)
                    return (ocs.ERROR, err.msg, {})
                except Exception as err:
                    self.log.error("Caught Exception during start call: {err}", err=err)
                    return (ocs.ERROR, f'CRASH: during param pre-processing: {str(err)}', {})

            # Mark as started.
            session = OpSession(self.next_session_id, op_name, app=self)
            self.next_session_id += 1
            self.sessions[op_name] = session

            # Schedule op to run (in worker thread or reactor)
            session.d = op.launch_deferred(session, params)
            session.d.addCallback(self._handle_task_return_val, session)
            session.d.addErrback(self._handle_task_error, session)

            return (ocs.OK, msg, session.encoded())

        else:
            self.log.warn("No task called {}".format(op_name))
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

        # Note that you can't just trust session.d.called to see if
        # the Op has ended.  For a "non-blocking" Operation
        # implementation (launched with task.deferLater and runs in
        # the reactor), the Deferred in session.d fires its first
        # callback, and sets called=True, when the start() function is
        # initiated, not when it completes.  Unfortunately this means
        # we have to trust session.status ... but that should be fine.
        done = False

        if session.status == 'done' or timeout is None:
            # Op is either done or we're happy to wait for it
            yield session.d
            done = True
        elif timeout < 0:
            # Op is running, but don't wait.
            pass
        else:
            # Op is running, wait for a limited duration.
            td = Deferred()
            reactor.callLater(timeout, td.callback, None)
            dl = DeferredList([session.d, td], fireOnOneCallback=True,
                              fireOnOneErrback=True, consumeErrors=True)
            try:
                yield dl
            except FirstError as e:
                assert e.index == 0  # i.e. session.d raised an error.
                td.cancel()
                e.subFailure.raiseException()
            else:
                done = (session.status == 'done')

        if done:
            success_str = {True: 'SUCCEEDED'}.get(session.success, 'FAILED')
            return (ocs.OK, f'Operation "{op_name}" is currently not running '
                    + f'({success_str}).', session.encoded())
        else:
            return (ocs.TIMEOUT, 'Operation "%s" still running; wait timed out.' % op_name,
                    session.encoded())

    def _stop_helper(self, stop_type, op_name, params):
        """Common stopper/aborter code for Process stop and Task
        abort.

        Args:
          stop_type (str): either 'stop' or 'abort'.
          op_name (str): the op_name.
          params (dict or None): Params to be passed to stopper
            function.

        """
        print(f'{stop_type} called for {op_name}')

        # Find the op and populate op_type, op, stopper, stopper_blocking.
        if op_name in self.tasks:
            op_type = 'task'
            op = self.tasks[op_name]
            stopper = op.aborter
            stopper_blocking = op.aborter_blocking
        elif op_name in self.processes:
            op_type = 'process'
            op = self.processes[op_name]
            stopper = op.stopper
            stopper_blocking = op.stopper_blocking
        else:
            return (ocs.ERROR, 'No operation called "%s".' % op_name, {})

        # Make sure the API function matches the op_type ...
        if (stop_type == 'stop' and op_type == 'task') or \
           (stop_type == 'abort' and op_type == 'process'):
            return (ocs.ERROR, f'Cannot "{stop_type}" "{op_name}" because '
                    'it is a "{op_type}".', {})

        session = self.sessions.get(op_name)
        if session is None:
            return (ocs.ERROR, 'No session active.', {})

        if session.status in ['stopping', 'done']:
            return (ocs.ERROR, f'The operation is already {session.status}', {})

        # Use callback/errback to print message to logs.
        def _callback(*args, **kw):
            try:
                ok, msg = args
            except BaseException:
                ok, msg = True, str(args)
            print(f'Stopper for "{op_name}" terminated with ok={ok} and '
                  f'message {msg}')

        def _errback(*args, **kw):
            print(f'Error calling stopper for "{op_name}"; args:',
                  args, kw)

        if stopper_blocking:
            # Launch the code in a thread.
            d2 = threads.deferToThread(stopper, session, params)
            d2.addCallback(_callback).addErrback(_errback)
        else:
            # Assume the stopper returns a Deferred (and will soon run
            # in the reactor).
            d2 = stopper(session, params)
            if not isinstance(d2, Deferred):
                # Warn but let it slide.  in the past the default was
                # to run the stopper in a worker thread.  Most
                # stoppers run very quickly so it is probably not
                # going to break much to have them run in the reactor.
                # Change this to an error after all Agents have been
                # updated for a while.
                print(f'WARNING: {op_type} {op_name} did not return '
                      'a Deferred. If the stopper is meant to be run '
                      'in a worker thread, the op should be registered '
                      'with stopper_blocking=True (Process) or '
                      'aborter_blocking=True (Task).  If the stopper '
                      'can safely run in the reactor, it should be '
                      'modified to return a Deferred.')
            else:
                d2.addCallback(_callback).addErrback(_errback)

        return (ocs.OK, f'Requested {stop_type} on {op_type} {op_name}".',
                session.encoded())

    def stop(self, op_name, params=None):
        """
        Initiate a Process stop routine.

        Returns (status, message, session).

        Possible values for status:

          ocs.ERROR: the specified op_name is not known, or refers to
            a Task.  Also returned if Process is known but not running.

          ocs.OK: the Process stop routine has been launched.
        """
        return self._stop_helper('stop', op_name, params)

    def abort(self, op_name, params=None):
        """
        Initiate a Task abort routine.

        Returns (status, message, session).

        Possible values for status:

          ocs.ERROR: the specified op_name is not known, or refers to
            a Process.  Also returned if Task is known but not running.

          ocs.OK: the Process stop routine has been launched.

        """
        return self._stop_helper('abort', op_name, params)

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


class AgentOp:
    def launch_deferred(self, session, params):
        """Launch the operation using the launcher function, either in
        a worker thread (self.blocking) or in the reactor (not
        self.blocking).  Return a Deferred.  Prior to executing the
        operation code, set session state to "running".

        """
        def _running_wrapper(session, params):
            session.set_status('running')
            return self.launcher(session, params)

        if self.blocking:
            # Launch, soon, in a blockable worker thread.
            return threads.deferToThread(_running_wrapper, session, params)
        else:
            # Launch, soon, in the main reactor thread.
            return task.deferLater(reactor, 0, _running_wrapper, session, params)


class AgentTask(AgentOp):
    def __init__(self, launcher, blocking=None, aborter=None,
                 aborter_blocking=None):
        self.launcher = launcher
        self.blocking = blocking
        self.aborter = aborter
        if aborter_blocking is None:
            aborter_blocking = blocking
        self.aborter_blocking = aborter_blocking
        self.docstring = launcher.__doc__

    def encoded(self):
        """Dict of static info for API self-description."""
        return {
            'blocking': self.blocking,
            'abortable': (self.aborter is not None),
            'docstring': self.docstring,
            'op_type': 'task',
        }


class AgentProcess(AgentOp):
    def __init__(self, launcher, stopper, blocking=None, stopper_blocking=None):
        self.launcher = launcher
        self.stopper = stopper
        self.blocking = blocking
        if stopper_blocking is None:
            stopper_blocking = blocking
        self.stopper_blocking = stopper_blocking
        self.docstring = launcher.__doc__

    def encoded(self):
        """Dict of static info for API self-description."""
        return {
            'blocking': self.blocking,
            'docstring': self.docstring,
            'op_type': 'process',
        }


#: These are the valid values for session.status.  Use like this:
#:
#: - None: uninitialized.
#: - ``starting``: the Operation code has been launched and is
#:   performing basic quick checks in anticipation of moving to the
#:   (longer term) "running" state.
#: - ``running``: the Operation code has performed basic quick checks
#:   and has started to do the requested thing.
#: - ``stopping``: the Operation code has acknowledged receipt of a
#:   "stop" or "abort" request.
#: - ``done``: the Operation has exited, either succesfully or not.
#:
SESSION_STATUS_CODES = [None, 'starting', 'running', 'stopping', 'done']


class OpSession:
    """When a caller requests that an Operation (Process or Task) is
    started, an OpSession object is created and is associated with
    that run of the Operation.  The Operation codes are given access
    to the OpSession object, and may update the status and post
    messages to the message buffer.  This is the preferred means for
    communicating Operation status to the caller.

    In the OCSAgent model, Operations may run in the main, "reactor"
    thread or in a worker "pool" thread.  Services provided by
    OpSession must support both these contexts (see, for example,
    add_message).

    Control Clients are given a copy of the latest session information
    in each response from the Operation API.  The format of that
    information is described in ``.encoded()``.

    The message buffer is purged periodically.

    """

    def __init__(self, session_id, op_name, status='starting',
                 app=None, purge_policy=None):
        # Note that some data members are used internally, while others are
        # communicated over WAMP to Agent control clients.

        self.messages = []  # entries are time-ordered (timestamp, text).
        self.data = {}      # Operation-specific data structures.
        self.degraded = False
        self.session_id = session_id
        self.op_name = op_name
        self.start_time = time.time()
        self.end_time = None
        self.app = app
        self.success = None
        self.status = None

        # This has to be the last call since it depends on init...
        self.set_status(status, timestamp=self.start_time)

        # Set up the log message purge.
        self.purge_policy = {
            'min_age_s': 3600,     # Time in seconds after which
                                   # messages can be discarded.
            'min_messages': 5,     # Number of messages to keep,
                                   # even if they have expired.
            'max_messages': 10000,  # Max number of messages to keep,
                                   # even if they have not expired.
        }
        if purge_policy is not None:
            self.purge_policy.update(purge_policy)
        self.purge_log()

    def purge_log(self):
        cutoff = time.time() - self.purge_policy['min_age_s']
        while ((len(self.messages) > self.purge_policy['max_messages'])
               or ((len(self.messages) > self.purge_policy['min_messages'])
               and self.messages[0][0] < cutoff)):
            self.messages.pop(0)
        # Set this purger to be called again in the future, at some
        # cadence based on the minimum message age.
        next_purge_time = max(self.purge_policy['min_age_s'] / 5, 600)
        self.purger = task.deferLater(reactor, next_purge_time, self.purge_log)

    def encoded(self):
        """Encode the session data in a dict.  This is the data structure that
        is returned to Control Clients using the Operation API, as the
        "session" information.  Note the returned object is a dict
        with entries described below.

        Returns
        -------
        session_id : int
          A unique identifier for a single session (a single "run" of
          the Operation).  When an Operation is initiated, a new
          session object is created and can be distinguished from
          other times the Operation has been run using this id.
        op_name : str
          The OCS Operation name.
        op_code : int
          The OpCode, which combines information from status, success,
          and degraded; see :class:`ocs.base.OpCode`.
        status : str
          The Operation run status (e.g. 'starting', 'done', ...).
          See :data:`ocs.ocs_agent.SESSION_STATUS_CODES`.
        degraded: bool
          A boolean flag (defaults to False) that an operation may set
          to indicate that it is not achieving its primary function
          (e.g. if it cannot establish connection to hardware).
        success : bool or None
          If the Operation Session has completed (`status == 'done'`),
          this indicates that the Operation was deemed successful.
          Prior to the completion of the operation, the value is None.
          The value could be False if the Operation reported failure,
          or if it crashed and failure was marked by the encapsulating
          OCS code.
        start_time : float
          The time the Operation Session started, as a unix timestamp.
        end_time : float or None
          The time the Operation Session ended, as a unix timestamp.
          While the Session is still on-going, this is None.
        data : dict
          This is an area for the Operation code to store custom
          information for Control Clients to consume.  See notes
          below.  This structure will be tested for strict JSON
          compliance, and certain translations performed (such as
          converting NaN to None/null).
        messages : list
          A buffer of messages posted by the Operation.  Each element
          of the list is a tuple, (timestamp, message) where timestamp
          is a unix timestamp and message is a string.

        Notes
        -----
        The ``data`` field may be used by Agent code to provide data
        that might be of interest to a user (whether human or
        automated), such as the most recent readings from a device,
        structured information about the configuration and progress of
        the Operation, or diagnostics.

        Please see developer documentation (:ref:`session_data`) for
        advice on structuring your Agent session data.

        """
        def json_safe(data, check_ok=False):
            """Convert data so it can be serialized and decoded on
            the other end.  This includes:

            - Converting numpy arrays and scalars to generic lists and
              Python basic types.

            - Converting NaN to None (although crossbar handles
              NaN/inf, web browsers may fail to deserialize the
              invalid JSON this requires).

            In the case of inf/-inf, a ValueError is raised.

            """
            if check_ok:
                output = json_safe(data)
                json.dumps(output, allow_nan=False)
                return output
            if isinstance(data, dict):
                return {k: json_safe(v) for k, v in data.items()}
            if isinstance(data, (list, tuple)):
                return [json_safe(x) for x in data]
            if hasattr(data, 'dtype'):
                # numpy arrays and scalars.
                return json_safe(data.tolist())
            if isinstance(data, (str, int, bool)):
                return data
            if isinstance(data, float):
                if math.isnan(data):
                    return None
                if not math.isfinite(data):
                    raise ValueError('Session.data cannot store inf/-inf; '
                                     'please convert to NaN.')
            # This could still be something weird but json.dumps will
            # probably reject it!
            return data

        return {'session_id': self.session_id,
                'op_name': self.op_name,
                'op_code': self.op_code.value,
                'status': self.status,
                'degraded': self.degraded,
                'success': self.success,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'data': json_safe(self.data, True),
                'messages': self.messages}

    @property
    def op_code(self):
        """
        Returns the OpCode for the given session.  This is what will be
        published to the registry's ``operation_status`` feed.
        """
        if self.status is None:
            return OpCode.NONE
        elif self.status == 'starting':
            return OpCode.STARTING
        elif self.status == 'running':
            if self.degraded:
                return OpCode.DEGRADED
            else:
                return OpCode.RUNNING
        elif self.status == 'stopping':
            return OpCode.STOPPING
        elif self.success:
            return OpCode.SUCCEEDED
        else:
            return OpCode.FAILED

    def set_status(self, status, timestamp=None):
        """Update the OpSession status and possibly post a message about it.

        Args:
            status (string): New value for status (see below).
            timestamp (float): timestamp for the operation.

        The possible values for status are:

        'starting'
            This status object has just been created, and the
            Operation launch code has yet to run.

        'running'
            The Operation is running.

        'stopping'
            The Operation is running, but a stop or abort has been
            requested.

        'done'
            The Operation is has terminated.  (Failure / success must
            be determined separately.)

        The only valid transitions are forward in the sequence
        [starting, running, stopping, done]; i.e. it is forbidden for
        the status of an OpSession to move from stopping to running.

        If this function is called from a worker thread, it will be
        scheduled to run in the reactor, and will block until that is
        complete.

        """
        if timestamp is None:
            timestamp = time.time()
        if not in_reactor_context():
            return threads.blockingCallFromThread(reactor,
                                                  self.set_status, status,
                                                  timestamp=timestamp)
        # Sanity check the status value.
        from_index = SESSION_STATUS_CODES.index(self.status)  # current status valid?
        to_index = SESSION_STATUS_CODES.index(status)        # new status valid?
        assert (to_index >= from_index)  # Only forward moves in status are permitted.

        if to_index == from_index:
            return

        self.status = status
        if status == 'done':
            self.end_time = timestamp

        try:
            self.add_message('Status is now "%s".' % status, timestamp=timestamp)
        except (TransportLost, Disconnected):
            self.app.log.error('setting session status to "{s}" failed. '
                               + 'transport lost or disconnected', s=status)

    def add_message(self, message, timestamp=None):
        """Add a log message to the OpSession messages buffer.

        Args:
            message (string): Message to append.
            timestamp (float): timestamp to tag the message.  The
                default, which is None, will cause the timestamp to be
                computed here and should be used in most cases.

        """
        if timestamp is None:
            timestamp = time.time()
        if not in_reactor_context():
            return reactor.callFromThread(self.add_message, message,
                                          timestamp=timestamp)
        self.messages.append((timestamp, message))
        # Make the app log this message, too.  The op_name and
        # session_id are an important provenance prefix.
        self.app.log.info('%s:%i %s' % (self.op_name, self.session_id, message))


class ParamError(Exception):
    def __init__(self, msg):
        self.msg = msg


class ParamHandler:
    """Helper for Agent Operation codes to extract params.  Supports type
    checking, has casting, and will raise errors that are
    automatically added to the session log and propagated to the
    caller in a useful way.

    There are two ways to use this.  The first and recommended way is
    to use the @param decorator.  Example::

        from ocs import ocs_agent

        class MyAgent:
            ...

            @ocs_agent.param('voltage', type=float)
            @ocs_agent.param('delay_time', default=1., type=float)
            @ocs_agent.param('other_action', default=None, cast=str)
            def my_task(self, session, params):
                # (Type checking and default substitution have been done already)
                voltage = params['voltage']
                delay_time = params['delay_time']
                other_action = params['other_action']
                ...

    When you use the @param decorator, the OCS code can check the
    parameters immediately when they are received from the client, and
    immediately return an error message to the client's start request
    (without even calling the Op start function)::

        OCSReply: ERROR : Param 'delay'=two_seconds is not of required type (<class 'float'>)
           (no session -- op has never run)


    A second possibility is to instantiate a ParamHandler at the start
    of your Op start function, and use it to extract parameters.
    Example::

        from ocs import ocs_agent

        class MyAgent:
            ...
            def my_task(self, session, params):
                params = ocs_agent.ParamHandler(params)
                # Mandatory, and cannot be None.
                voltage = params.get('voltage', type=float)
                # Optional, defaults to 1.
                delay_time = params.get('delay_time', default=1., type=float)
                # Optional, interpret as string, but defaults to None.
                other_action = params.get('other_action', default=None, cast=str)
                ...

    In this case, errors will not be immediatley returned to the user,
    but the Operation will quickly fail, and the error message will
    show up in the message log::

        OCSReply: OK : Operation "my_task" is currently not running (FAILED).
          my_task[session=1]; status=done with ERROR 0.115665 s ago, took 0.000864 s
          messages (4 of 4):
            1629464204.780 Status is now "starting".
            1629464204.780 Status is now "running".
            1629464204.781 ERROR: Param 'delay'=two_seconds is not of required type (<class 'float'>)
            1629464204.781 Status is now "done".
          other keys in .session: op_code, data

    """

    def __init__(self, params):
        if params is None:
            params = {}
        self._params = params
        self._checked = set()

    def get(self, key, default=ParamError(''), check=None, cast=None, type=None,
            choices=None, treat_none_as_missing=True):
        """Retrieve a value from the wrapped params dict, with optional type
        checking, casting, and validity checks.  If a parameter is
        found to be missing, or its value not valid, then a ParamError
        is raised.

        In Agent Op implementations, the ParamError will be caught by
        the API wrapper and automatically propagated to the caller.
        The Operation session will be marked as "done", with
        success=False.

        This works best if the implementation validates all parameters
        *before* beginning any Operation activities!

        Args
        ----
        key : str
          The name of the parameter to extract.
        default : any
          The value to use if the value is not set.  If this isn't
          explicitly set, then a missing key causes an error to be
          raised (see also the treat_none_as_missing arg).
        check : callable
          A function that will validate the argument; if the function
          returns False then a ParamError will be raised.
        cast : callable
          A function to run on the value to convert it.  For example
          ``cast=str.lower`` would help convert user argument
          "Voltage" to value "voltage".
        type : type
          Class to which the result will be compared, unless it is
          ``None``.  Note that if you pass ``type=float``, ``int``
          values will automatically be cast to ``float`` and accepted
          as valid.
        choices : list
          Acceptable values for the parameter.  This is checked after
          casting.
        treat_none_as_missing : bool
          Determines whether a value of ``None`` for a parameter
          should be treated in the same way as if the parameter were
          not set at all.  See notes.

        Returns
        -------
        The fully processed value.

        Notes
        -----

        The default behavior is to treat ``{'param': None}`` as the
        same as ``{}``; i.e. passing ``None`` as the value for a
        parameter is the same as leaving the parameter unset.  In both
        of these cases, unless a ``default=...`` is specified, a
        ``ParamError`` will be raised.  Note this doesn't preclude you
        from setting ``default=None``, which would effectively convert
        ``{}`` to ``{'param': None}``.  If you really need to block
        ``{}`` while allowing ``{'param': None}`` to be taken at face
        value, then set ``treat_none_as_missing=False``.

        The cast function, if specified, is applied before the type,
        choices, and check arguments are processed.  If the value (or
        the substituted default value) is ``None``, then any specified
        cast and checks will not be performed.

        """
        self._checked.add(key)
        value = self._params.get(key, None)
        is_unset = value is None and \
            (treat_none_as_missing or key not in self._params)
        if is_unset:
            if isinstance(default, ParamError):
                raise ParamError(f"Param '{key}' is required and must not be None")
            value = default
        if value is not None:
            if cast is not None:
                try:
                    value = cast(value)
                except BaseException:
                    raise ParamError(f"Param '{key}'={value} could not be cast to {cast}.")
            if type is not None:
                # Free cast from int to float.
                if type is float and isinstance(value, int):
                    value = float(value)
                # Fix type after json conversion
                if type is tuple and isinstance(value, list) and cast in [tuple, None]:
                    value = tuple(value)
                if not isinstance(value, type):
                    raise ParamError(f"Param '{key}'={value} is not of required type ({type})")
            if choices is not None:
                if value not in choices:
                    raise ParamError(f"Param '{key}'={value} is not in allowed set ({choices})")
            if check is not None:
                if not check(value):
                    raise ParamError(f"Param '{key}' failed validity check (see docs?).")
        return value

    def batch(self, instructions, check_for_strays=True):
        """
        Supports the @params decorator ... see code.
        """
        params = {}
        for key, kw in instructions:
            if key == '_':
                pass
            elif key == '_no_check_strays':
                check_for_strays = False
            else:
                params[key] = self.get(key, **kw)
        if check_for_strays:
            self.check_for_strays()
        return params

    def check_for_strays(self, ignore=[]):
        """Raise a ParamError if there were arguments passed in that have not
        yet been extracted with .get().  Keys passed in ignore (list)
        will be ignored regardless.

        """
        weird_args = [k for k in self._params.keys()
                      if k not in self._checked and k not in ignore]
        if len(weird_args):
            raise ParamError(f"params included unexpected values: {weird_args}")


def param(key, **kwargs):
    """Decorator for Agent operation functions to assist with checking
    params prior to actually trying to execute the code.  Example::

      class MyAgent:
        ...
        @param('voltage', type=float)
        @param('delay', default=0., type=float)
        @inlineCallbacks
        def set_voltage(self, session, params):
          ...

    Note the ``@param`` decorators should be all together, and
    outermost (listed first).  This is because the current
    implementation caches data in the decorated function (or
    generator) directly, and additional decorators will conceal that.

    See :class:`ocs.ocs_agent.ParamHandler` for more details.  Note the
    signature for @param is the same as for :func:`ParamHandler.get`.

    """
    # Validate the kwargs by passing them to "get" with trivial data.
    if 'default' in kwargs:
        ParamHandler({}).get(key, **kwargs)
    else:
        ParamHandler({}).get(key, default=None, **kwargs)
    # Start a cache and append these args to it...

    def deco(func):
        if not hasattr(func, '_ocs_prescreen'):
            setattr(func, '_ocs_prescreen', [])
        func._ocs_prescreen.append((key, kwargs))
        return func
    return deco
