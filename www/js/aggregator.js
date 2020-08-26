/* AggregatorAgent UI */

function aggregator_populate(p, base_id, args) {
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

        .process('record')
        .op_header({client: client})
        .status_indicator()
    ;

    //
    // Left panel: monitor.
    //
    var ui2 = new OcsUiHelper(base_id);
    ui2.dest($('#' + base_id + '-viewport'))
        .set_boxes(false)
        .panel()
        .banner('Aggregator Monitor')
        .text_indicator('heartbeat', 'Connection', {center: true})
        .text_indicator('current_file', 'current_file')
        .indicator('providers')
    ;

    // Update handlers -- propagate operation session information into
    // indicators.

    client.add_watcher('record', 5., function(op_name, method, stat, msg, session) {

        ui1.set_status('record', session);
        if (!session.data || session.status != 'running') {
            ui2.ind('', 'current_file').val('');
            ui2.ind('', 'providers').html('');
            return;
        }
        var d = session.data;
        ui2.ind('', 'current_file').val(d.current_file);
        var list = $('<ul>');
        $.each(d.providers, function(feed_name, info) {
            var ago = human_timespan(timestamp_now() - info.last_refresh);
            list.append($('<li>').append(`${feed_name} - ${ago} ago`));
        });
        ui2.ind('', 'providers').html('Providers:<br />').append(list);
    });

    // Keep an eye on agent presence.
    ocs_connection.agent_list.subscribe(base_id, args.address, function (addr, conn_ok) {
        ui2.set_connection_status('', 'heartbeat', conn_ok,
                                  {input_containers: [base_id + '-controls']});
    });

    // Return a destructor function -- stop all timers!
    return (function() {
        ocs_connection.agent_list.unsubscribe(base_id);
        client.destroy();
    });
}

// Register the constructor in the main tab manager.
tabman.constructors['AggregatorAgent'] = aggregator_populate;
