var debugs = {};         // For stashing debug data.

var reconnection_timer = null;
var reconnection_delay = 5.;
var reconnection_count = 0;

var query_op_timer = null;
var successful_connect = null;

/* log(msg)
 *
 * This function must always me available, even if it does nothing.
 */

function log(msg) {
    var log = $("#messages");
    log.html(log.html() + msg + '<br>');
    log.scrollTop(log[0].scrollHeight - log.height());
}
ocs_log = log;

function create_hider(clickable_id, hideable_id, show_text, hide_text, hide_it) {
    
    var elem = $(clickable_id).on('click', function () {
        if ($(hideable_id).toggle().is(':visible'))
            $(clickable_id).html(hide_text);
        else
            $(clickable_id).html(show_text);
    });
    if (hide_it) {
        $(hideable_id).toggle();
        elem.html(show_text);
    } else
        elem.html(hide_text);
    return elem;
}

function init() {
    $(document).ready(function() {
        log('Page init function is running...');
        log('Autobahn version:', autobahn.version);

        // Set up defaults -- these could be fed from elsewhere... ?
        $('#wamp_router').val('ws://localhost:8001/ws');
        $('#wamp_realm').val('test_realm');
        $('#target_agent').val('');

        // Hiders.
        create_hider('#connection_form_table_toggle',
                     '#connection_form_table',
                     ' [show]', ' [hide]', false).addClass('clickable');
        create_hider('#messages_hider',
                     '#messages',
                     ' [show]', ' [hide]', true).addClass('clickable');

        connect();
    });
}

/** AgentList
 *
 *  For maintaining the list of active Agents; uses heartbeat feed(s)
 *  to keep list up-to-date.
 */

function AgentList () {
    this.agent_list = [];
}

AgentList.prototype = {

    update_agent_info: function(info) {
        var addr = info.agent_address;
        if (!this.agent_list.includes(addr)) {
            this.agent_list.push(addr);
            this.agent_list.sort();
            var table = $('<table>');
            //table.append($('<tr><td class="data_h">Agents</td></tr>'));
            this.agent_list.forEach(function (x) {
                link = $('<span class="clickable">' + x + '</span>').on(
                    'click', function () {
                        $('#target_agent').val(x);
                        query_agent();
                    });
                table.append($('<tr>').append($('<td class="data_1">').append(link)));
                debugs['x'] = link;
            });
            var dump = $('#agent_list').html('').append(table).append('<br>');
        }
    }
}

/* Interface attachments. */

function connect() {
    url = $('#wamp_router').val();
    realm = $('#wamp_realm').val();

    // See connection options at...
    // https://github.com/crossbario/autobahn-js/blob/master/packages/autobahn/lib/connection.js
    //
    // We set max_retries=0 and manage retries ourself, so that
    // retries always go to address in the input boxes.
    ocs = new autobahn.Connection({
	url: url,
        realm: realm,
        max_retries: 0,
    });

    ocs.onopen = function(_session, details) {
        ocs_log('connected.');
        reconnection_count = 0;

        $('#connection_checkmark').html(' &#10003;');
        var agent_list = new AgentList();

        // Monitor heartbeat feeds to see what Agents are online.
        ocs.session.subscribe('observatory..feeds.heartbeat', function (args, kwargs, details) {
            var info = args[0][1];
            agent_list.update_agent_info(info);
        }, {'match': 'wildcard'});

        // Try subscribe?
        var agent_addr = $('#target_agent').val();
        var feed_id = $('#target_feed').val();
        if (agent_addr && feed_id) {
            var feed_to_monitor = agent_addr + '.feeds.' + feed_id;
            $('#feed_monitor_legend').html('Feed: ' + feed_to_monitor);
            ocs.session.subscribe(
                feed_to_monitor,
                function (args, kwargs, details) {
                    var timestr = get_date_time_string(null, ' ');
                    var text = '<b>' + feed_to_monitor + ' @ ' + timestr +
                        '</b><br>\n' +
                        '<p>' + JSON.stringify(args[0]) +'</p>';
                    $('#feed_monitor').html(text);
                });
        }
    

    };
    ocs.onclose = function(reason, details) {
        // Reasons observed:
        // - "lost" - crossbar dropped out.
        // - "closed" - app has called close().
        // - "unreachable" - failed to connect (onopen never called)
        ocs_log('closed because: ' + reason);

        $('#connection_checkmark').html(' &#10005;');
        $('#feed_monitor').html('(Cleared on connection reset.)');

        // If this looks like an orderly deliberate shutdown, do a
        // reconnect.
        if (reason == 'closed')
            connect();
        else if (reconnection_count++ < 1000) {
            reconnection_timer = setInterval(connect, reconnection_delay*1000.);
        }
    };

    log('Trying connection to "' + url + '", realm "' + realm + '"...');
    $('#connection_checkmark').html(' &#10067;');

    if (reconnection_timer)
        clearInterval(reconnection_timer);

    ocs.open();
}

function query_agent() {
    // Requests the Agent's interface (Operations and Feeds), using
    // AgentClient.scan.  The results are loaded into the "Interface"
    // window.

    if (ocs == null) return;
    agent_addr = $('#target_agent').val();
    client = new AgentClient(ocs, agent_addr);

    client.scan(function () {
        log('Client scan completed.');
        var summary = $('<table>');
        $('#target_op').val('');
        
        summary.append($('<tr><td class="data_h">Processes</td></tr>'));
        client.procs.forEach(function (x) {
            var link = $('<span class="clickable">' + x[0] + '</span><br />');
            link.on('click', function () {
                $('#target_op').val(x[0]);
                query_op(true);
            });
            summary.append($('<tr>').append(($('<td class="data_1">').append(link))));
        });
        summary.append($('<tr><td class="data_h">Tasks</td></tr>'));
        client.tasks.forEach(function (x) {
            var link = $('<span class="clickable">' + x[0] + '</span><br />');
            link.on('click', function () {
                $('#target_op').val(x[0]);
                query_op(true);
            });
            summary.append($('<tr>').append(($('<td class="data_1">').append(link))));
        });
        summary.append($('<tr>').append($('<td class="data_h">').append('Feeds')));//</td></tr>'));
        client.feeds.forEach(function (x) {
            var link = $('<span class="clickable">' + x[0] + '</span><br />');
            link.on('click', function () {
                $('#target_feed').val(x[0]);
                subscribe_feed();
            });
            summary.append($('<tr>').append(($('<td class="data_1">').append(link))));
        });
        $('#interface_summary').html('').append(summary);
    });
    debugs['client'] = client;

    var msgh = new MessageBuffer();
    msgh.callback = function () {
        text = '';
        for (i=Math.max(0, this.messages.length - 10); i < this.messages.length; i++) {
            timestr = get_date_time_string(this.messages[i][0], ' ');
            text += timestr + ' ' + this.messages[i][1] + '<br>\n';
        }
        $('#status_tasks').html(text);
        log("Now there are " + this.messages.length + " messages.");
    };

    client.onSession = function (result) {
        session = result[2];
        if (session.op_name == 'dump_agent_info') {
            msgh.update(session);
        }
    };
}

function query_op(reset_query) {
    // Request the status of a particular Operation from a particular
    // Agent.  If reset_query, then the display area is cleared before
    // the request goes out... otherwise, it is left as-is so it won't
    // flicker if the data have not changed.

    if (ocs == null) return;
    agent_addr = $('#target_agent').val();
    agent_op = $('#target_op').val();

    var query_op_valid = (agent_addr && agent_op);
    if (!query_op_valid ||  reset_query)
        $('#op_status').empty();

    if (!query_op_valid)
        return;
        
    client = new AgentClient(ocs, agent_addr);
    //$('#op_status_legend').html('Op Session Info');

    client.status(agent_op).then(function (args, kwargs) {

        debugs['status'] = args;
        var data = args[2]; // The first two args are, like, [0, "Session active."].

        var timestr = get_date_time_string(null, ' ');
        var text = '<b>' + client.address + '.ops.' + agent_op + ' @ ' +
            timestr + '</b><br>\n';
        
        var out = $('<div>');
        fmt_pair = function(k, v) {
            k = k + '&nbsp;'.repeat(Math.max(0,10 - k.length));
            return k + ' ' + v + '<br>\n';
        };
        fmt_time = function(t) {
            if (!t)
                return '(null)';
            return t.toFixed(3) + ' ' + get_date_time_string(t, ' ');
        };

        out.append(text);
        out.append(fmt_pair('Op Name:', data.op_name) +
                   fmt_pair('Status:', data.status) +
                   fmt_pair('Started:', fmt_time(data.start_time)) +
                   fmt_pair('Ended:', fmt_time(data.end_time)) +
                   fmt_pair('Data:', data.data));
        out.append('Messages:<br>\n');
        msgs = $('<div class="autopop_border">');
        if (data.messages)
            data.messages.forEach(function (msg) {
                timestr = get_date_time_string(msg[0], ' ');
                msgs.append('<p class="hanging_logmsg">' + timestr + ': ' + msg[1] + '</p>');
            });
        out.append(msgs);

        $('#op_status').empty().append(out);

        // Poll for updates.
        if (query_op_timer)
            clearTimeout(query_op_timer);
        query_op_timer = setTimeout(function () { query_op(false); }, 2000);

    });
}

function subscribe_feed() {
    if (ocs == null) return;

    // Only way to subscribe is to reconnect.
    ocs.close();
}
