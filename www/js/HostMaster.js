/* HostMaster UI */

function HostMaster_populate(p, base_id, args) {
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
        .process('master')
        .op_header()
        .status_indicator()
        .task('die')
        .op_header()
        .status_indicator()
    ;

    //
    // Left panel: monitor.
    //
    var ui2 = new OcsUiHelper(base_id, client);
    ui2.dest($('#' + base_id + '-viewport'))
        .set_boxes(false)
        .set_context('v')
        .banner('HostMaster Monitor')
        .text_indicator('heartbeat', 'Connection', {center: true})
        .banner('Managed Agents')
        .indicator('children')
    ;

    // Update handlers -- propagate operation session information into
    // indicators.
    var child_count = 0;
    var props = {
        instance_id: {name: "instance-id"},
        class_name: {name: "class-name"},
        next_action: {name: "current", center: true},
        target_state: {name: "target", center: true},
        req: ""
    };
    var child_data = new TableMan(base_id + '-table', props, ["up", "down"],
                                  function(button, instance_id) {
                                      console.log('click', button, instance_id);
                                      client.start_task('update', {
                                          requests:  [[instance_id, button]]
                                      });
                                  });

    ui2.get('v', 'children').append(
        $('<form class="hm_ui">').attr('id', child_data.base_id));

    client.add_watcher('master', 5., function(op_name, method, stat, msg, session) {
        ui1.set_status('master', session);
        if (!session.data || session.status != 'running') {
            ui2.get('v', 'children').val('');
            return;
        }
        $.each(session.data.child_states, function(idx, info) {
            child_data.update(info.instance_id, info);
        });
        child_data.populate(true);
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

function TableMan(base_id, prop_list, but_list, handler) {
    this.base_id = base_id;
    this.prop_list = prop_list;
    this.but_list = but_list;
    this.handler = handler;
    this.data = {};
    this.count = 0;
    this.updates = {};
    this.new_rows = {};
    this.base = null;
}

TableMan.prototype = {
    new_row: function(ident, data) {
        this.data[ident] = data;
        this.data[ident]._rowid = this.base_id + '-r' + this.count;
        this.data[ident].req = '*';
        this.count++;
        this.updates[ident] = true;
        this.new_rows[ident] = true;
    },
    update: function(ident, data) {
        var self = this;
        if (!self.data[ident])
            return self.new_row(ident, data);
        var same = true;
        data.req = '';
        $.each(self.prop_list, (p, pn) => {
            if (data[p] != self.data[ident][p]) {
                self.data[ident][p] = data[p];
                same = false;
                self.data[ident].req = '*';
            }
        });
        if (!same)
            self.updates[ident] = true;
    },
    populate: function(do_all) {
        // If first time, write the header.
        if (!this.base) {
            this.base = $('#' + this.base_id);
            $.each(this.prop_list, (p, pp) => {
                var div = $('<div>').addClass('hm_header').html(pp.name);
                if (pp.center)
                    div.addClass('hm_center');
                this.base.append(div);
            });
            $.each(this.but_list, () => {
                this.base.append($('<div>'));
            });
        }
        // Create any new data rows
        $.each(this.new_rows, (inst, is_new_row) => {
            if (!is_new_row)
                return;
            var data = this.data[inst];
            $.each(this.prop_list, (prop, pp) => {
                var div = $('<div>').html(data[prop]).attr('id', data._rowid + '-' + prop);
                if (pp.center)
                    div.addClass('hm_center');
                this.base.append(div);
            });
            $.each(this.but_list, (i, but_text) => {
                var but = $(`<input type="button" value="${but_text}" class="obviously_clickable">`)
                    .on('click', () => {
                        data.req = '*';
                        this.handler(but_text, inst);
                        this.populate();
                    });
                this.base.append(but);
            });
            this.new_rows[inst] = false;
        });
        // Update cells with changed data.
        $.each(this.data, (ident) => {
            if (this.updates[ident] || do_all) {
                $.each(this.prop_list, (prop, pn) => {
                    var cell = $('#' + this.data[ident]._rowid + '-' + prop);
                    cell.html(this.data[ident][prop]);
                });
                this.updates[ident] = false;
            }
        });
    },
};

// Register the constructor in the main tab manager.
tabman.constructors['HostMaster'] = HostMaster_populate;
