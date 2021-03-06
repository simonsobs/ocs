var ocs_debugs = {};     // For stashing debug data.

/* ocs_log(msg)
 *
 * If the ocs_log function is not defined prior to this point, a
 * simple console.log is connected.
 */

if (typeof ocs_log == 'undefined') {
    console.log('ocs_log not defined, using console.');
    function ocs_log(msg) {
        console.log(msg);
    }
}

function OCSConnection(url_func, realm_func)
{
    this.url_func = url_func;
    this.realm_func = realm_func;

    // Hooks; assign handlers with .on(trigger, func).
    this.handlers = {
        'connected': null,
        'try_connect': null,
        'disconnected': null,
    };

    this.feeds = {};

    this.connection = null;

    this._reconnection = {
        timer: null,
        delay: 5.0,
        count: 0,
        requested: false };
}

OCSConnection.prototype = {
    connect : function()
    {
        if (this.connection)
            this.connection.close();

        this_ocs = this;

        url = this.url_func();
        realm = this.realm_func();

        // See connection options at...
        // https://github.com/crossbario/autobahn-js/blob/master/packages/autobahn/lib/connection.js
        //
        // We set max_retries=0 and manage retries ourself, so that
        // retries always go to address in the input boxes.
        c = new autobahn.Connection({
	    url: url,
            realm: realm,
            max_retries: 0,
        });

        c.onopen = function(_session, details) {
            ocs_log('connected.');
            this_ocs._reconnection.count = 0;

            if (this_ocs.handlers.connected)
                this_ocs.handlers.connected();

            var agent_list = new AgentList();
            this_ocs.agent_list = agent_list;

            // Monitor heartbeat feeds to see what Agents are online.
            c.session.subscribe('observatory..feeds.heartbeat', function (args, kwargs, details) {
                var info = args[0][1];
                agent_list.handle_heartbeat_info(info);
            }, {'match': 'wildcard'});

            // Subscribe for all registered feed handlers.
            for (const [feed_name, handler] of Object.entries(this_ocs.feeds))
                c.session.subscribe(feed_name, handler);
        };

        c.onclose = function(reason, details) {
            // Reasons observed:
            // - "lost" - crossbar dropped out.
            // - "closed" - app has called close() -- but this also occurs
            //   if the realm could not be joined.
            // - "unreachable" - failed to connect (onopen never called)
            ocs_log('closed because: ' + reason + ' : ' + details.message);

            if (this_ocs.handlers.disconnected)
                this_ocs.handlers.disconnected();

            // Flush each feed handler.
            for (const [feed_name, handler] of Object.entries(this_ocs.feeds))
                handler(null, null, null);

            this_ocs.connection = null;

            // If this looks like an orderly deliberate shutdown, do an
            // immediate reconnect.  Otherwise, keep the pace low...
            if (reason == 'closed' && this_ocs._reconnection.requested) {
                this_ocs.connect();
            } else if (this_ocs._reconnection.count++ < 1000) {
                this_ocs._reconnection.timer = setInterval(this_ocs.connect, this_ocs._reconnection.delay*1000.);
            }
            this_ocs._reconnection.requested = false;
        };

        log('Trying connection to "' + url + '", realm "' + realm + '"...');
        if (this_ocs.handlers.try_connect)
            this_ocs.handlers.try_connect();

        if (this_ocs._reconnection.timer)
            clearInterval(this_ocs._reconnection.timer);

        this.connection = c;
        c.open();
    },

    start: function() {
        this.connect();
    },

    on: function(action, handler) {
        this.handlers[action] = handler;
    },

    // Temporary single feed registration system.
    set_feed: function(feed_name, handler) {
        this.feeds = {};
        this.feeds[feed_name] = handler;
        this._reconnection.requested = true;
        this.connection.close();
    },

    get_client: function(agent_address) {
        return new AgentClient(this, agent_address);
    },
}

/* AgentClient
 *
 * Tracks the status of a client.  Instantiate with an OCSConnection
 * (will will maintain an autobahn.Connection internally), and the
 * agent address.
 */

function AgentClient(_ocs, address) {
    this.ocs = _ocs;
    this.address = address;
    this.tasks = null;
    this.procs = null;
    this.feeds = null;
    this.agent_class = null;
    this.watchers = {};
}

AgentClient.prototype = {

    // scan
    //
    // Uses the "get_api" method to get the lists of all tasks,
    // processes, and feeds of the Agent.  The task and process items
    // include session status information, as well.

    scan : function(callback) {
        // Try first on the "new" API; fall back to the old one (now
        // deprecated).
        client = this;
        this.ocs.connection.session.call(this.address, ['get_api'])
            .then( function(result) {
                // Calling an invalid method address seems to return
                // null result, rather than raise a catchable.
                if (!result) {
                    client.scan_old_api(callback);
                    return;
                }
                // New API.
                client.tasks = result.tasks;
                client.procs = result.processes;
                client.feeds = result.feeds;
                client.agent_class = result.agent_class;
                if (callback != null)
                    callback();
            });
    },

    scan_old_api : function(callback) {
        console.log('Warning, ' + this.address + ' does not support "get_api" call.');
        client = this;
        var d = new autobahn.when.defer();
        var counter = 3;
        d.promise.then(function() {
            if (callback != null)
                callback();
        });
        this.ocs.connection.session.call(this.address, ['get_tasks']).then(
            function(result) {
                client.tasks = [];
                if (result != null)
                    client.tasks = result;
                if (--counter == 0)
                    d.resolve();
            });
        this.ocs.connection.session.call(this.address, ['get_processes']).then(
            function(result) {
                client.procs = [];
                if (result != null)
                    client.procs = result;
                if (--counter == 0)
                    d.resolve();
            });
        this.ocs.connection.session.call(this.address, ['get_feeds']).then(
            function(result) {
                client.feeds = [];
                if (result != null)
                    client.feeds = result;
                if (--counter == 0)
                    d.resolve();
            });
    },

    // dispatch
    //
    // Issue a request on the Agent's task/proc API.  This API always
    // returns a response of the form (code, message, session).
    //
    // @param method      API request: start, wait, stop, abort, status.
    // @param op_name     Name of the Task or Process.
    // @param params      Object with key-value parameters for the method.

    dispatch : function(method, op_name, params) {
        client = this;
        _p = [method, op_name, params];

        // Wrap all API calls to call our onSession handler before
        // returning to the invoking agent.
        var d = new autobahn.when.defer();
        client.ocs.connection.session.call(client.address + '.ops', _p).then(
            function (args) {
                // OCS responds with a simple list, args = [exit_code,
                // message, session].
                if (client.watchers[op_name])
                    $.each(client.watchers[op_name].handlers, (i, h) =>
                           h.f(op_name, method, args[0], args[1], args[2]));
                d.resolve(args);
            });
        return d.promise;
    },

    // task/proc API
    //
    // These functions should be used when working with the task/proc API.
    //

    start_task : function(task_name, params) {
        return this.dispatch('start', task_name, params);
    },

    wait_task : function(task_name, params) {
        return this.dispatch('wait', task_name, params);
    },

    // run_task is the equivalent of start_task followed by wait_task.
    run_task : function(task_name, params) {
        client = this;
        var d = new autobahn.when.defer();
        client.start_task(task_name, params).then( function (result) {
            ocs_log(result[1] + ' code ' + result[0]);
            client.wait_task(task_name, params).then(function (result) {
                d.resolve(result);
            });
        });
        return d.promise;
    },

    abort_task : function(task_name) {
        return this.dispatch('abort', task_name, []);
    },

    start_proc : function(proc_name, params) {
        return this.dispatch('start', proc_name, params);
    },

    stop_proc : function(proc_name) {
        return this.dispatch('stop', proc_name, []);
    },

    status : function(op_name) {
        return this.dispatch('status', op_name, []);
    },

    // API for attaching session information handlers.
    add_watcher: function(op_name, span, handler) {
        // op_name: Name of operation to handle.
        // span: Interval at which to poll the operation (if 0, do not poll).
        // handler: function to call on each status reply.
        //
        // The signature of handler should be (op_name, method_name,
        // exit_code, message, session).
        if (!this.watchers[op_name]) {
            this.watchers[op_name] = {
                last_update: 0.,
                timer: null,
                span: 0,
                handlers: [],
            };
        }
        var current_span = this.watchers[op_name].span;
        if (span > 0 && (current_span == 0 || current_span > span)) {
            this.watchers[op_name].span = span;
            clearInterval(this.watchers[op_name].timer);
            client = this;
            this.watchers[op_name].timer = setInterval(function () {
                client.status(op_name);
            }, span * 1000.);
            // If ~slow update, trigger one immediately too.
            if (span >= 1.)
                client.status(op_name);
        }
        this.watchers[op_name].handlers.push({f: handler, span: span});
    },

    destroy: function() {
        // Stop all timers.
        client = this;
        $.each(this.watchers, (op_name, data) => clearInterval(data.timer))
    },
}

function MessageBuffer() {
    this.latest = null;
    this.messages = [];
    this.callback = null;
}

MessageBuffer.prototype = {
    // update : merge the sessions message buffer into the present
    update : function(session) {
        mbuf = this;
        if (session == null || session.messages == null || session.messages.length == 0)
            return;
        if (mbuf.latest == null)
            mbuf.messages = session.messages;
        else {
            m = mbuf.messages;
            session.messages.forEach(function (x) {
                log('ding ' + mbuf.latest);
                if (x[0] > mbuf.latest) {
                    m.push(x);
                }
            });
        }
        mbuf.latest = session.messages[session.messages.length-1][0];
        log(mbuf.latest);
        if (mbuf.callback)
            mbuf.callback();
    }
}


/*
 * Utilities.
 */

function get_date_time_string(timestamp, joiner) {
    function twodig(x) {
        if (x<10) return '0'+x;
        return x;
    }

    if (!timestamp)
        timestamp = Date.now() / 1000.;

    var d = new Date(parseInt(timestamp)*1000);
    if (isNaN(d.getTime())) {
        return ['??', '??'];
    }
    var datestr = d.getUTCFullYear() + '-' + twodig(d.getUTCMonth()+1) + '-'
                + twodig(d.getUTCDate());
    var timestr = twodig(d.getUTCHours()) + ':' + twodig(d.getUTCMinutes()) + ':' +
                  twodig(d.getUTCSeconds());

    if (!joiner)
        return [datestr, timestr];

    return datestr + joiner + timestr;
}

var HUMANITIES = [
    {max:    60*2, unit:     1, label: 'secs'},
    {max:  3600*2, unit:    60, label: 'mins'},
    {max: 86400*2, unit:  3600, label: 'hours'},
    {max:    null, unit: 86400, label: 'days'},
];

function human_timespan(delta, precision) {
    /* Convert delta, a time in seconds, to a textual representation
     * in comprehensible units with ~2+precision sigfigs.  E.g. 86401
     * becomes '1.00 days'. */
    var spec;
    var i;
    if (!precision)
        precision = 1;
    for (i=0; i<HUMANITIES.length; i++) {
        spec = HUMANITIES[i];
        if (!spec.max || Math.abs(delta) < spec.max)
            break;
    }
    return (delta / spec.unit).toFixed(precision) + ' ' + spec.label;
}

function timestamp_now() {
    var now = new Date();
    return now.getTime() / 1000.;
}
