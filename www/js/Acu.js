/* AcuAgent UI */

var acu_POINT = 'go_to';
var acu_BORESIGHT = 'set_boresight';
var acu_RUN_SCAN = 'run_specified_scan';
var acu_STOP_CLEAR = 'stop_and_clear';

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

        .task(acu_POINT)
        .op_header()
        .text_input('az', 'Azimuth (deg)')
        .text_input('el', 'Elevation (deg)')
        .status_indicator()

        .task(acu_BORESIGHT)
        .op_header()
        .text_input('third', 'Value (deg)')
        .status_indicator()

        .task(acu_STOP_CLEAR)
        .op_header()
        .status_indicator()

        .task(acu_RUN_SCAN)
        .op_header()
        .text_input('az0', 'Az1')
        .text_input('az1', 'Az2')
        .text_input('el',  'El')
        .text_input('azvel', 'Vel')
        .text_input('acc',   'Acc')
        .text_input('ntimes', 'Count')
        .status_indicator()

        .process('monitor')
        .op_header()
        .text_indicator('update_rate', 'Updates (Hz)')
        .status_indicator()

        .process('broadcast')
        .op_header()
        .text_indicator('sample_rate', 'Updates (Hz)')
        .status_indicator()
    ;

    // Define any action handlers that require processing of
    // parameters.  Any task() or process() declared in the UI with a
    // client: option will have default handlers set up.  But anything
    // that needs validation or type conversion of input data must be
    // explicitly assigned liked this.
    ui1.on(acu_POINT, 'start', function(data) {
        var params = {};
        params.az = parseFloat(data.az);
        params.el = parseFloat(data.el);
        params.wait = 1.;
        client.start_task(acu_POINT, params);
    });

    ui1.on(acu_BORESIGHT, 'start', function(data) {
        var params = {};
        params.b = parseFloat(data.third);
        client.start_task(acu_BORESIGHT, params);
    });

    ui1.on(acu_RUN_SCAN, 'start', function(data) {
        var params = {};
        // azpts', 'el', 'azvel', 'acc', 'ntimes
        params.scantype = 'linear_turnaround';
        params.azpts = [parseFloat(data.az0), parseFloat(data.az1)];
        params.el = parseFloat(data.el);
        params.azvel = parseFloat(data.azvel);
        params.acc = parseFloat(data.acc);
        params.ntimes = parseFloat(data.ntimes);
        client.start_task(acu_RUN_SCAN, params);
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

    var data_table = new ValueTable(base_id + '-table');
    ui2.get('v', 'warnings').append(
        data_table.get_form());


    // Update handlers -- propagate operation session information into
    // indicators.

    // One handler for the status... this should be canned!
    $.each([acu_POINT, acu_BORESIGHT, acu_RUN_SCAN, acu_STOP_CLEAR,
            'monitor', 'broadcast'],
           function (idx, op_name) {
               client.add_watcher(op_name, 1., function(op_name, method, stat, msg, session) {
                   ui1.set_status(op_name, session);
               });
           });

    client.add_watcher('monitor', 2., function(op_name, method, stat, msg, session) {
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

        data_table.update(d);
        data_table.populate(false);
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

//
// ValueTable -- manager for the table of child agents.
//

function ValueTable(base_id) {
    this.base_id = base_id;
    this.data = {};
    this.count = 0;
    this.updates = {};
    this.new_rows = {};
    this.del_rows = [];
    this.base = null;
}

ValueTable.prototype = {
    get_form: function() {
        //Create a form tag and return it; sets up the grid layout with
        //the right number of columns.
        var el = $('<form class="acu_ui">').attr('id', this.base_id);
        var layout = "3fr 1fr";
        el.css({
            "display": "grid",
            "font-family": "monospace",
            "grid-gap": "5px",
            "align-items": "center",
            "grid-template-columns": layout});
        return el
    },
    update: function(all_data) {
        var self = this;
        var missing = Object.getOwnPropertyNames(self.data);
        $.each(all_data, function(key, value) {
            var idx = missing.indexOf(key);
            if (value === null)
                value = "null";
            else
                value = value.toString();
            if (idx < 0) {
                self.data[key] = {
                    value: value,
                    _rowid: self.base_id + '-r' + self.count,
                    _color: self.count % 2,
                };
                self.count++;
                self.new_rows[key] = true;
            } else {
                missing.splice(idx, 1);
                if (self.data[key].value !== value) {
                    self.data[key].value = value;
                    self.updates[key] = true;
                }
            }
        });
        self.del_rows = missing;
    },
    populate: function(do_all) {
        // If first time, write the header.
        if (!this.base) {
            var div1 = $('<div>').addClass('hm_header').html('Key');
            var div2 = $('<div>').addClass('hm_header acu_value').html('Value');
            this.base = $('#' + this.base_id);
            this.base.append(div1);
            this.base.append(div2);
        }
        // Remove stale rows
        while (this.del_rows.length) {
            var key = this.del_rows.pop();
            $('.' + this.data[key]._rowid).remove();
            delete this.data[key];
        }

        // Create any new data rows
        $.each(this.new_rows, (key, is_new_row) => {
            if (!is_new_row)
                return;
            var data = this.data[key];
            var div1 = $('<div>').html(key).css('height', '100%');
            var div2 = $('<div>').addClass('acu_value').attr('id', data._rowid + '-value').css('height', '100%');
            div1.addClass(data._rowid);
            div2.addClass(data._rowid);
            if (data._color)
                div1.css("background-color", "#ccc");
            this.base.append(div1);
            this.base.append(div2);
            this.new_rows[key] = false;
            this.updates[key] = true;
        });

        // Update cells with changed data.
        $.each(this.data, (key, row) => {
            if (this.updates[key] || do_all) {
                var cell = $('#' + row._rowid + '-value');
                cell.html(row.value);
                if (row.value == "true")
                    cell.css("background-color", "#faa");
                else if (row.value == "false")
                    cell.css("background-color", "#0b6");
                this.updates[key] = false;
            }
        });
    },
};


// Register the constructor in the main tab manager.
tabman.constructors['ACUAgent'] = Acu_populate;
