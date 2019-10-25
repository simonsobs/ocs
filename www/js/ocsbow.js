var ocs = null;          // The autobahn.Connection.
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

/* get_ocs(url, realm)
 *
 * For now this just returns the autobahn.Connection object, after
 * .open() has been called.
 */

function get_ocs(url, realm) {
    var ocs = new autobahn.Connection({
        url: url,
        realm: realm,
    });
    ocs.onopen = function(_session, details) {
        //session = _session;
        ocs_log('connected.');
    };
    ocs.onclose = function(reason, details) {
        ocs_debugs.reason = reason;
        ocs_log('closed.');
    };
    ocs.open();
    return ocs;
}

/* AgentClient
 *
 * Tracks the status of a client.  Instantiate with an Ocs handle
 * (autobahn.Connection) and the agent address.
 */

function AgentClient(_ocs, address) {
    this.ocs = _ocs;
    this.address = address;
    this.tasks = null;
    this.procs = null;
    this.feeds = null;
    this.messages = null;

    this.onSession = this._default_session_handler;
    this.handlers = {};

    client = this;
    this.ocs.session.subscribe(address + '.feed', function (args, kwargs, details) {
        ocs_debugs.feed = args;
        client.messages = args[0];
    });
}

AgentClient.prototype = {
    scan : function(callback) {
        client = this;
        var d = new autobahn.when.defer();
        var counter = 3;
        d.promise.then(function() {
            if (callback != null)
                callback();
        });
        this.ocs.session.call(this.address, ['get_tasks']).then(
            function(result) {
                client.tasks = [];
                if (result != null)
                    client.tasks = result;
                if (--counter == 0)
                    d.resolve();
            });
        this.ocs.session.call(this.address, ['get_processes']).then(
            function(result) {
                client.procs = [];
                if (result != null)
                    client.procs = result;
                if (--counter == 0)
                    d.resolve();
            });
        this.ocs.session.call(this.address, ['get_feeds']).then(
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

    dispatch : function(op, task_name, params) {
        client = this;
        _p = [op, task_name];
        _p.push.apply(_p, params);  // _p.extend(params);

        // Wrap all API calls to call our onSession handler before
        // returning to the invoking agent.
        var d = new autobahn.when.defer();
        client.ocs.session.call(client.address + '.ops', _p).then(
            function (result) {
                if (client.onSession != null) {
                    client.onSession(result);
                }
                d.resolve(result);
            });
        return d.promise;
    },

    _default_session_handler : function(result) {
        session = result[2];
        ocs_log('all-sess: ' + session['op_name'] + ' status is ' + session['status']);
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

    start_proc : function(proc_name, params) {
        return this.dispatch('start', proc_name, params);
    },

    stop_proc : function(proc_name) {
        return this.dispatch('stop', proc_name, []);
    },

    status : function(op_name) {
        return this.dispatch('status', op_name, []);
    }

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
