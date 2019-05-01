var debugs = {};         // For stashing debug data.

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

function init() {
    $(document).ready(function() {
        log('Page init function is running...');
        log('Autobahn version:', autobahn.version);
        // Set up defaults -- these could be fed from elsewhere.
        $('#wamp_router').val('ws://localhost:8001/ws');
        $('#wamp_realm').val('debug_realm');
        $('#registry_addr').val('observatory.registry');
        $('#target_agent').val('observatory.agg1');
        connect();
    });
}

function AgentList () {
    this.agent_list = [];
}

AgentList.prototype = {
    update_agent_info: function(agent_name) {
        this.agent_list.push(agent_name);
        text = '';
        this.agent_list.forEach(function (x) {
            text += x + '<br>';
        });
        $('#registry_dump').html(text);
    }
}

function connect() {
    url = $('#wamp_router').val();
    realm = $('#wamp_realm').val();

    log('Connecting to "' + url + '", realm "' + realm + '"...');

    ocs = new autobahn.Connection({
	url: url,
        realm: realm,
    });
    ocs.onopen = function(_session, details) {
        ocs_log('connected.');
        var agent_list = new AgentList();
        reg_addr = $('#registry_addr').val();
        debugs['reg'] = [];
        ocs.session.subscribe(reg_addr + '.feeds.agent_activity',
                              function (args, kwargs, details) {
                                  args.forEach(function (x) {
                                      addr = x[0][1]['agent_address'];
                                      ocs_log(addr);
                                      agent_list.update_agent_info(addr);
                                  });
                              });
    };
    ocs.onclose = function(reason, details) {
        debugs.reason = reason;
        ocs_log('closed.');
    };
    ocs.open();
}

function query_registry() {
    reg_addr = $('#registry_addr').val();
    reg_client = new AgentClient(ocs, reg_addr);
    reg_client.run_task('dump_agent_info', []).then(
        function (result) {log('dump_agent_info finished.'); });
}

function query_interface() {
    if (ocs == null) return;
    agent_addr = $('#target_agent').val();
    client = new AgentClient(ocs, agent_addr);
    client.scan(function () {
        log('Client scan completed.');
        iface_summary = 'Processes:<br>';
        client.procs.forEach(function (x) {
            iface_summary += '&nbsp;&nbsp;' + x[0] + '<br>';
        });
        iface_summary += '<br>Tasks:<br>';
        client.tasks.forEach(function (x) {
            iface_summary += '&nbsp;&nbsp;' + x[0] + '<br>';
        });
        iface_summary += '<br>Feeds:<br>';
        client.feeds.forEach(function (x) {
            iface_summary += '&nbsp;&nbsp;' + x[0] + '<br>';
        });
        $('#interface_summary').html(iface_summary);
    });
    debugs['client'] = client;

    var msgh = new MessageBuffer();
    msgh.callback = function () {
        text = '';
        for (i=Math.max(0, this.messages.length - 10); i < this.messages.length; i++) {
            dt = get_date_time_strings(this.messages[i][0]);
            text += dt[0] + ' ' + dt[1] + ' ' + this.messages[i][1] + '<br>\n';
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

function query_operation() {
    if (ocs == null) return;
    agent_addr = $('#target_agent').val();
    agent_op = $('#target_op').val();
    client = new AgentClient(ocs, agent_addr);
    $('#op_status').html('Updating...');
    client.status(agent_op).then(function (args, kwargs) {
        ocs_log('status returned.');
        $('#op_status').html(args[2]['status']);
        debugs['status'] = args;});
}
