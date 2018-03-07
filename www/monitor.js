var connection = null;
var session = null;
var agent_addr = 'observatory.dets1';

var debugs = {};

// A print function for debugging.
function log(msg) {
    var log = document.getElementById("messages");
    log.innerHTML = msg + "<br>" + log.innerHTML;
}

function run_task(task_name) {
    log('Requesting start of task "' + task_name + '"....');
    connection.session.call(agent_addr + '.ops', ['start', task_name]).then(
        function (result) {
            // err, msg, session = result.
            log(result[1]);
        });
}

function start_proc(proc_name) {
    log('Requesting start of process "' + proc_name + '"....');
    connection.session.call(agent_addr + '.ops', ['start', proc_name]).then(
        function (result) {
            // err, msg, session = result.
            log(result[1]);
        });
}

function stop_proc(proc_name) {
    log('Requesting stop of process "' + proc_name + '"....');
    connection.session.call(agent_addr + '.ops', ['stop', proc_name]).then(
        function (result) {
            // err, msg, session = result.
            log(result[1]);
        });
}

var status_class_map = {
    'done': 'op_status_done',
    'running': 'op_status_running',
    'starting': 'op_status_starting',
    'stopping': 'op_status_stopping'
    };

function update_status(source, session) {
    var text = '<span class="op_name">' + session.op_name + '</span>';
    var classstr = "op_status " + status_class_map[session.status];
    text += '<span class="' + classstr + '">' + session.status + '</span>';
    text += '<hr>';
    text += '<div class="op_time_box"><p>';
    t0 = get_date_time_strings(session.start_time);
    t1 = get_date_time_strings(session.end_time);
    text += '<table><tr><td>'
          + 'Started:</td><td><span class="op_start_time">' + t0[0] + ' ' + t0[1] + '</span>'
          + '</td></tr><tr><td>'
          + 'Ended:</td><td><span class="op_end_time">' + t1[0] + ' ' + t1[1] + '</span>'
          + '</td></tr></table>';
    text += '</p></div>';
    text += '<div>Messages:<br>';
    var i = session.messages.length - 2;
    while (i < session.messages.length) {
        if (i>=0) {
            var m = session.messages[i];
            t0 = get_date_time_strings(m[0]);
            text += '<span class="op_log_message">' + t0[1] + ':' + m[1] + '</span>';
        }
        i++;
    }
    text += '</div>';

    var target = $('#status_' + session.op_name);
    target.html(text);
}

function init() {
    
    $(document).ready(function() {
        log('starting.');

        console.log("Ok, Autobahn loaded", autobahn.version);
        var url = "ws://localhost:8001/ws";

        connection = new autobahn.Connection({
            url: url,
            realm: "realm1"
        });
        connection.onopen = function(_session, details) {
            session = _session;
            log('connected.');
            var pop_status = function (result) {
                debugs['tlist'] = result;
                result.forEach(function (row) {
                    if (row[1] != null)
                        update_status('feed', row[1]);
                    log('Reloading ' + row[0]);
                });
            };
            session.call(agent_addr, ['get_tasks']).then(pop_status);
            session.call(agent_addr, ['get_processes']).then(pop_status);
            
            session.subscribe(agent_addr + '.feed', function (args, kwargs, details) {
                debugs.feed = args;
                update_status('feed', args[0]);
            });
            
        };
        connection.onclose = function(reason, details) {
            log('closed.');
        };

        connection.open();
        
        log('done init.');
    });
}

function get_date_time_strings(timestamp) {
    function twodig(x) {
        if (x<10) return '0'+x;
        return x;
    }

    var d = new Date(parseInt(timestamp)*1000);
    if (isNaN(d.getTime())) {
        return ['??', '??'];
    }
    var datestr = d.getUTCFullYear() + '-' + twodig(d.getUTCMonth()+1) + '-'
                + twodig(d.getUTCDate());
    var timestr = twodig(d.getUTCHours()) + ':' + twodig(d.getUTCMinutes()) + ':' +
                  twodig(d.getUTCSeconds());
    return [datestr, timestr];
}
