/* HostManager UI */

function HostManager_populate(p, base_id, args) {
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
        .process('manager')
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
        .banner('HostManager Monitor')
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
        next_action: {name: "current", center: true,
                      recoder: function (info) {
                          if (info.next_action != 'down' &&
                              info.stability <= 0.5)
                              return 'unstable';
                          return info.next_action;
                      }},
        target_state: {name: "target", center: true},
    };
    var child_data = new KidsTable(base_id + '-table', props, ["up", "down"],
                                   function(button, instance_id) {
                                      this.data[instance_id].target_state = `(${button})`;
                                      this.updates[instance_id] = true;
                                      this.populate();
                                      client.start_task('update', {
                                          requests:  [[instance_id, button]]
                                      });
                                  });
    ui2.get('v', 'children').append(
        child_data.get_form());

    client.add_watcher('manager', 5., function(op_name, method, stat, msg, session) {
        ui1.set_status('manager', session);
        if (!session.data || session.status != 'running') {
            ui2.get('v', 'children').val('');
            return;
        }
        child_data.update(session.data.child_states);
        child_data.populate(false);
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
// KidsTable -- manager for the table of child agents.
//

function KidsTable(base_id, prop_list, but_list, handler) {
    this.base_id = base_id;
    this.prop_list = prop_list;
    this.but_list = but_list;
    this.handler = handler;
    this.data = {};
    this.count = 0;
    this.updates = {};
    this.new_rows = {};
    this.del_rows = [];
    this.base = null;
}

KidsTable.prototype = {
    get_form: function() {
        //Create a form tag and return it; sets up the grid layout with
        //the right number of columns.
        var el = $('<form class="hm_ui">').attr('id', this.base_id);
        var layout = "3fr 3fr";
        $.each(this.prop_list, function () {
            layout = layout + " 1fr";
        });
        el.css("grid-template-columns", layout);// "3fr 3fr 1fr 1fr 1fr 1fr");
        return el
    },
    update: function(child_states) {
        var self = this;
        var missing = Object.getOwnPropertyNames(self.data);
        let found = [];
        $.each(child_states, function(idx, data) {
            ident = data.instance_id;
            if (found.includes(ident)) {
                // HostManager shouldn't ever do this!
                console.log(`HostManager encountered second block for agent_id=${ident}, ignoring.`);
                return;
            }
            found.push(ident);
            var idx = missing.indexOf(ident);
            if (idx < 0) {
                self.data[ident] = data;
                self.data[ident]._rowid = self.base_id + '-r' + self.count;
                self.count++;
                self.new_rows[ident] = true;
            } else {
                missing.splice(idx, 1);
                var same = true;
                $.each(self.prop_list, (p, pn) => {
                    var d = data[p];
                    if (pn.recoder)
                        d = pn.recoder(data);
                    if (p != self.data[ident][p]) {
                        self.data[ident][p] = d;
                        same = false;
                    }
                });
                self.updates[ident] = !same;
            }
        });
        self.del_rows = missing;
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
        // Remove stale rows
        while (this.del_rows.length) {
            var inst = this.del_rows.pop();
            $('.' + this.data[inst]._rowid).remove();
            delete this.data[inst];
        }

        // Create any new data rows
        $.each(this.new_rows, (inst, is_new_row) => {
            if (!is_new_row)
                return;
            var data = this.data[inst];
            $.each(this.prop_list, (prop, pp) => {
                var div = $('<div>').html(data[prop]).attr('id', data._rowid + '-' + prop);
                div.addClass(data._rowid);
                if (pp.center)
                    div.addClass('hm_center');
                this.base.append(div);
            });
            $.each(this.but_list, (i, but_text) => {
                var but = $(`<input type="button" value="${but_text}" class="obviously_clickable">`)
                    .addClass(data._rowid)
                    .on('click', () => {
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
tabman.constructors['HostManager'] = HostManager_populate;
