/* Generic Agent UI */

function generic_populate(p, base_id, args) {
    /* See interface definition in monitor_ui.js preamble.
     *
     * The following fields in args are required:
     *
     *   address: the OCS address of the Agent
     */

    // Layout: two block_units, which will sit side-by-side in
    // wide-screen mode but slip into a single column when the browser
    // is narrowed.  Half of operations on one side, half on the other.
    p.append($('<div>').append(
        '<p>Caution! This is a generic control UI.  It may not be safe or useful to run ' +
            'operations through this interface, because parameters cannot be ' +
            'specified.</p>'));
    p.append($('<div class="block_holder">')
             .append($(`<div class="block_unit" id=${base_id}-controls1>`))
             .append($(`<div class="block_unit" id=${base_id}-controls2>`)));


    var client = new AgentClient(ocs_connection, args.address);

    var ui1 = new OcsUiHelper(base_id);
    ui1.dest($('#' + base_id + '-controls1'));

    var ui2 = new OcsUiHelper(base_id);
    ui2.dest($('#' + base_id + '-controls2'));

    client.scan(function () {
        var n_items = client.tasks.length + client.procs.length + 1;
        var i = 1;
        ui1
            .set_context('v')
            .banner('Monitor for ' + args.address)
            .text_indicator('heartbeat', 'Connection', {center: true})
        ;

        $.each({task: client.tasks, process: client.procs},
               function(op_type, op_list) {
                   $.each(op_list, function(key, val) {
                       var dest = ui1;
                       if (i++ >= n_items / 2)
                           dest = ui2;
                       var op_name = val[0];
                       dest.set_context(op_name, op_type)
                           .op_header({client: client})
                           .status_indicator()
                       ;
                       client.add_watcher(op_name, 1., function(op_name, method, stat, msg, session) {
                           dest.set_status(op_name, session);
                       });
                   })
               });
    });

    // Keep an eye on agent presence.
    ocs_connection.agent_list.subscribe(base_id, args.address, function (addr, conn_ok) {
        ui1.set_connection_status('v', 'heartbeat', conn_ok,
                                  {input_containers: [base_id + '-controls']});
    });

    // Return a destructor function -- stop all timers!
    return (function() {
        ocs_connection.agent_list.unsubscribe(base_id);
        client.destroy();
    });
}

// Register the constructor in the main tab manager.
tabman.constructors['GenericAgent'] = generic_populate;
