/* AcuAgent UI */

function Acu_populate(p, base_id, args) {
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
    var ui1 = new OcsUiHelper(base_id, client);
    ui1.dest($('#' + base_id + '-controls'))

        .task('point')
        .op_header()
        .text_input('az', 'Azimuth (deg)')
        .text_input('el', 'Elevation (deg)')
        .status_indicator()

        .task('boresight_rotation')
        .op_header()
        .text_input('third', 'Value (deg)')
        .status_indicator()

        .task('track_fromfile')
        .op_header()
        .status_indicator()

        .process('monitor')
        .op_header()
        .text_indicator('update_rate', 'Updates (Hz)')
        .status_indicator()

        .process('udp_monitor')
        .op_header()
        .text_indicator('update_rate', 'Updates (Hz)')
        .status_indicator()
    ;

    // Define any action handlers that require processing of
    // parameters.  Any task() or process() declared in the UI with a
    // client: option will have default handlers set up.  But anything
    // that needs validation or type conversion of input data must be
    // explicitly assigned liked this.
    ui1.on('point', 'start', function(data) {
        var params = {};
        params.az = parseFloat(data.az);
        params.el = parseFloat(data.el);
        client.start_task('point', params);
    });

    //
    // Left panel: monitor.
    //
    var ui2 = new OcsUiHelper(base_id);
    ui2.dest($('#' + base_id + '-viewport'))
        .set_boxes(false)
        .set_context('v')
        .banner('Acu Monitor')
        .text_indicator('heartbeat', 'Connection', {center: true})
        .text_indicator('az', 'Azimuth')
        .text_indicator('el', 'Elevation')
        .text_indicator('third', 'Boresight')
        .text_indicator('as_of', 'As of')
        .indicator('warnings')
    ;

    // Update handlers -- propagate operation session information into
    // indicators.

//    client.add_watcher('delay_task', 1., function(op_name, method, stat, msg, session) {
//        ui1.set_status('delay_task', session);
//        if (!session.data)
//            return;
//        var so_far = session.data.delay_so_far;
//        var reqd = session.data.requested_delay;
//        if (reqd)
//            ui2.get('v', 'delay_reqd').val(reqd.toFixed(3));
//        if (so_far)
//            ui2.get('v', 'delay_so_far').val(so_far.toFixed(3));
//        if (reqd && so_far)
//            ui2.get('v', 'delay_progress').progressbar({value: 100 * so_far / reqd});
//    });
//

    // One handler for the status... this should be canned!
    $.each(['point', 'boresight_rotation', 'track_fromfile', 'monitor', 'udp_monitor'],
           function (idx, op_name) {
               client.add_watcher(op_name, 1., function(op_name, method, stat, msg, session) {
                   ui1.set_status(op_name, session);
               });
           });

    client.add_watcher('monitor', 2., function(op_name, method, stat, msg, session) {
        //ui1.set_status('monitor', session);
        var d = session.data;
        $.each({'az': 'Azimuth', 'el': 'Elevation', 'third': 'Boresight'}, function (short, long) {
            var mode = d[`${long} mode`];
            var pos = d[`${long} current position`].toFixed(4);
            ui2.get('v', short).val(`[${mode}]  ${pos}`);
        });
        // Convert time to
        var as_of = Date.UTC(d['Year'],'00','01','00','00','00') / 1000.
            + 86400. * (d['Time'] - 1);
        var ago = human_timespan(timestamp_now() - as_of);
        ui2.get('v', 'as_of').val(`${ago} ago`);

        var list = $('<ul>');
        $.each(d, function (key, value) {
            list.append($('<li>').append(`${key}: ${value}`));
        });
        ui2.get('v', 'warnings').html('Warnings:<br />').append(list);


//  {"Time":266.82982488104,"Year":2020,"Azimuth mode":"Preset","Azimuth commanded position":89.9998,"Azimuth current position":89.9998,"Azimuth current velocity":0,"Azimuth average position error":0,"Azimuth peak position error":0,"Azimuth computer disabled":false,"Azimuth axis disabled":false,"Azimuth axis in stop":false,"Azimuth brakes released":true,"Azimuth stop at LCP":false,"Azimuth power on":true,"Azimuth CCW limit: 2nd emergency":false,"Azimuth CCW limit: emergency":false,"Azimuth CCW limit: operating":false,"Azimuth CCW limit: pre-limit":false,"Azimuth CCW limit: operating (ACU software limit)":false,"Azimuth CCW limit: pre-limit (ACU software limit)":false,"Azimuth CW limit: pre-limit (ACU software limit)":false,"Azimuth CW limit: operating (ACU software limit)":false,"Azimuth CW limit: pre-limit":false,"Azimuth CW limit: operating":false,"Azimuth CW limit: emergency":false,"Azimuth CW limit: 2nd emergency":false,"Azimuth summary fault":false,"Azimuth servo failure":false,"Azimuth motion error":false,"Azimuth brake 1 failure":false,"Azimuth brake 2 failure":false,"Azimuth brake warning":false,"Azimuth breaker failure":false,"Azimuth amplifier 1 failure":false,"Azimuth amplifier 2 failure":false,"Azimuth motor 1 overtemperature":false,"Azimuth motor 2 overtemperature":false,"Azimuth AUX 1 mode selected":false,"Azimuth AUX 2 mode selected":false,"Azimuth overspeed":false,"Azimuth amplifier power cylce interlock":false,"Azimuth regeneration resistor 1 overtemperature":false,"Azimuth regeneration resistor 2 overtemperature":false,"Azimuth CAN bus amplifier 1 communication failure":false,"Azimuth CAN bus amplifier 2 communication failure":false,"Azimuth encoder failure":false,"Azimuth oscillation warning":false,"Azimuth oscillation alarm":false,"Azimuth tacho failure":false,"Azimuth immobile":false,"Azimuth overcurrent motor 1":false,"Azimuth overcurrent motor 2":false,"Elevation mode":"Preset","Elevation commanded position":55,"Elevation current position":55,"Elevation current velocity":0,"Elevation average position error":0,"Elevation peak position error":0,"Elevation computer disabled":false,"Elevation axis disabled":false,"Elevation axis in stop":false,"Elevation brakes released":false,"Elevation stop at LCP":false,"Elevation power on":false,"Elevation Down limit: extended emergency (co-moving shield off)":false,"Elevation Down limit: extended operating (co-moving shield off)":false,"Elevation Down limit: emergency":false,"Elevation Down limit: operating":false,"Elevation Down limit: pre-limit":false,"Elevation Down limit: operating (ACU software limit)":false,"Elevation Down limit: pre-limit (ACU software limit)":false,"Elevation Up limit: pre-limit (ACU software limit)":false,"Elevation Up limit: operating (ACU software limit)":false,"Elevation Up limit: pre-limit":false,"Elevation Up limit: operating":false,"Elevation Up limit: emergency":false,"Elevation summary fault":false,"Elevation servo failure":false,"Elevation motion error":false,"Elevation brake 1 failure":false,"Elevation brake warning":false,"Elevation breaker failure":false,"Elevation amplifier 1 failure":false,"Elevation motor 1 overtemp":false,"Elevation overspeed":false,"Elevation amplifier power cylce interlock":false,"Elevation regeneration resistor 1 overtemperature":false,"Elevation CAN bus amplifier 1 communication failure":false,"Elevation encoder failure":false,"Elevation oscillation warning":false,"Elevation oscillation alarm":false,"Elevation immobile":false,"Elevation overcurrent motor 1":false,"Boresight mode":"Stop","Boresight commanded position":null,"Boresight current position":100,"Boresight computer disabled":false,"Boresight axis disabled":false,"Boresight axis in stop":true,"Boresight brakes released":false,"Boresight stop at LCP":false,"Boresight power on":true,"Boresight CCW limit: emergency":false,"Boresight CCW limit: operating":false,"Boresight CCW limit: pre-limit":false,"Boresight CCW limit: operating (ACU software limit)":false,"Boresight CCW limit: pre-limit (ACU software limit)":false,"Boresight CW limit: pre-limit (ACU software limit)":false,"Boresight CW limit: operating (ACU software limit)":false,"Boresight CW limit: pre-limit":false,"Boresight CW limit: operating":false,"Boresight CW limit: emergency":false,"Boresight summary fault":false,"Boresight servo failure":false,"Boresight motion error":false,"Boresight brake 1 failure":false,"Boresight brake 2 failure":false,"Boresight brake warning":false,"Boresight breaker failure":false,"Boresight amplifier 1 failure":false,"Boresight amplifier 2 failure":false,"Boresight motor 1 overtemperature":false,"Boresight motor 2 overtemperature":false,"Boresight AUX 1 mode selected":false,"Boresight AUX 2 mode selected":false,"Boresight overspeed":false,"Boresight amplifier power cylce interlock":false,"Boresight regeneration resistor 1 overtemperature":false,"Boresight regeneration resistor 2 overtemperature":false,"Boresight CAN bus amplifier 1 communication failure":false,"Boresight CAN bus amplifier 2 communication failure":false,"Boresight encoder failure":false,"Boresight oscillation warning":false,"Boresight oscillation alarm":false,"Boresight tacho failure":false,"Boresight immobile":false,"Boresight overcurrent motor 1":false,"Boresight overcurrent motor 2":false,"General summary fault":false,"E-Stop servo drive cabinet":false,"E-Stop service pole":false,"E-Stop AZ movable":false,"Key Switch Bypass Emergency Limit":false,"PCU operation":false,"Safe":false,"Power failure (latched)":false,"Lightning protection surge arresters":false,"Power failure (not latched)":false,"24V power failure":false,"General Breaker failure":false,"Cabinet Overtemperature":false,"Ambient temperature low (operation inhibited)":false,"Co-Moving Shield off":false,"PLC-ACU interface error":false,"Qty of free program track stack positions":9999,"ACU in remote mode":true,"ACU fan failure":true}

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
tabman.constructors['AcuAgent'] = Acu_populate;
