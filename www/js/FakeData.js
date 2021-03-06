/* FakeDataAgent UI */

function FakeData_populate(p, base_id, args) {
    /* See interface definition in monitor_ui.js preamble.
     *
     * The following fields in args are required:
     *
     *   address: the OCS address of the Agent
     */

    // Layout: two block_units, which will sit side-by-side in
    // wide-screen mode but slip into a single column when the browser
    // is narrowed.
    p.append($('<div class="block_holder">')
             .append($(`<div class="block_unit" id=${base_id}-viewport>`))
             .append($(`<div class="block_unit" id=${base_id}-controls>`)));


    var client = new AgentClient(ocs_connection, args.address);
    ocs_debugs['client'] = client;

    //
    // Right panel: controls.
    //
    var ui1 = new OcsUiHelper(base_id);
    ui1.dest($('#' + base_id + '-controls'))

        .task('delay_task')
        .op_header()
        .text_input('delay', 'Delay (s)')
        .dropdown('delay_box', 'Suggestions', ['', '10', '100'])
        .status_indicator()

        .process('acq')
        .op_header({client: client})
        .status_indicator()
    ;

    // Define any action handlers that require processing of
    // parameters.  Any task() or process() declared in the UI with a
    // client: option will have default handlers set up.  But anything
    // that needs validation or type conversion of input data must be
    // explicitly assigned liked this.
    ui1.on('delay_task', 'start', function(data) {
        var params = {};
        data.delay = parseFloat(data.delay);
        data.delay_box = parseFloat(data.delay_box);
        if (!isNaN(data.delay))
            params.delay = data.delay;
        else if (!isNaN(data.delay_box))
            params.delay = data.delay_box;

        if (params.delay && params.delay < 0)
            alert("Can't send negative delay value!");
        else
            client.start_task('delay_task', params);
    });

    //
    // Left panel: monitor.
    //
    var ui2 = new OcsUiHelper(base_id);
    ui2.dest($('#' + base_id + '-viewport'))
        .set_boxes(false)
        .set_context('v')
        .banner('FakeData Monitor')
        .text_indicator('heartbeat', 'Connection', {center: true})
        .text_indicator('delay_reqd', 'Delay Requested')
        .text_indicator('delay_so_far', 'Delay So Far')
        .progressbar('delay_progress', 'Progress')
        .text_indicator('acq_process_state', 'Acq Process State')
    ;

    // Update handlers -- propagate operation session information into
    // indicators.

    client.add_watcher('delay_task', 1., function(op_name, method, stat, msg, session) {
        ui1.set_status('delay_task', session);
        if (!session.data)
            return;
        var so_far = session.data.delay_so_far;
        var reqd = session.data.requested_delay;
        if (reqd)
            ui2.get('v', 'delay_reqd').val(reqd.toFixed(3));
        if (so_far)
            ui2.get('v', 'delay_so_far').val(so_far.toFixed(3));
        if (reqd && so_far)
            ui2.get('v', 'delay_progress').progressbar({value: 100 * so_far / reqd});
    });

    client.add_watcher('acq', 2., function(op_name, method, stat, msg, session) {
        ui1.set_status('acq', session);
        ui2.get('v', 'acq_process_state').val(session.status);
    });

    // Keep an eye on agent presence.
    ocs_connection.agent_list.subscribe(base_id, args.address, function (addr, conn_ok) {
        ui2.set_connection_status('v', 'heartbeat', conn_ok,
                                  {input_containers: [base_id + '-controls']});
    });

    // Return a destructor function -- stop all timers!
    return (function() {
        ocs_connection.agent_list.unsubscribe(base_id);
        client.destroy();
    });
}

// Register the constructor in the main tab manager.
tabman.constructors['FakeDataAgent'] = FakeData_populate;
