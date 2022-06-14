/*
  monitor_ui.js

  Support classes for monitor.js.  Include this before monitor.js and
  before any scripts that use the Ui construction functions.

  The TabManager class is used to create new tabs with Agent UIs for a
  particular Agent instance.  The UIs themselves can be implemented
  "manually" or by using OcsUiHelper objects to generate simple
  controls and indicators.

  The TabManager calls constructor functions associated with
  particular Agent Classes to construct controls and indicators.  The
  prototype for such constructor functions is:

    function constructor(p, base_id, args)

      @param {Object} p : Jquery element (probably a $('<div>')) where
          the UI should be inserted.
      @param {string} base_id : Unique string to use as a base for all
          element ids generated for the UI.
      @param {Object} args : Additional parameters for creating the UI and
          making any necessary Agent/other connections.

      The content of args is specific to the constructor but at a
      minimum you should expect 'address'.

      The constructor should return a destructor function that will be
      called after removing the UI elements.
    
 */



function TabManager() {
    /* reg: a map from UI name (probably the Agent address) to an
     * object with some UI info (such as the id of the div for the
     * UI); see add function.
     */
    this.ui_reg = {};

    /* constructors: a map from AgentClass name (string) to
     * constructor function.  Specific Agent UIs can add themselves to
     * this registry.
     */
    this.constructors = {};

    // Internal counter for generating ~unique ids for each UI panel.
    this._next_id = 1000000;

    /* We haven't bothered with putting the methods into .prototype,
       since this is likely to be a singleton class. */

    this.add = function(name, agent_class, args) {
        /* Create an Agent-specific UI tab.
         *
         * @param {string} name: the identifier that will be used for
         *     the UI.  This is likely to simply be the Agent address.
         * @param {string or function} agent_class: If this is a
         *     function, it is used to construct UI Tab.  If it is a
         *     string, it is used as a key to find a constructor
         *     function in this.constructors.  If it is null, the user
         *     will be presented with a modal dialog to select a
         *     constructor function (from this.constructors).
         * @param {Object} args: additional arguments needed to
         *     construct the UI.  For Agent UIs, the OCS address of
         *     the Agent must be present in member 'address'.
         *
         * @returns {Object} The UI info from this.ui_reg.
         *
         * Note that if the 'name' already has an associated UI tab, a
         * new tab is not created but the info block is still
         * returned.
         */

        if (this.ui_reg[name])
            return this.ui_reg[name];
        
        if (agent_class instanceof Function) {
            pop_func = agent_class;
        } else if (!agent_class || !this.constructors[agent_class]) {
            /* If the agent_class is null or does not match any
             * registered constructor, allow the user to select a
             * constructor from a modal dialog. */
            var ap = $('#agent_class_picker');
            var list = $('<ul>');
            var tabman = this;
            $.each(this.constructors, function(key, val) {
                var item = $(`<span>`).append(`${key}`).addClass('clickable').on('click', function () {
                    // Call self with the agent_class now populated.
                    if (val)
                        tabman.add(name, val, args);
                    $.modal.close();
                });
                list.append($(`<li>`).append(item));
            });
            ap.html(`<p>Select the agent class appropriate for use with ` +
                    `<tt>${name}</tt> which is of class <tt>${agent_class}</tt>:</p>`);
            ap.append(list);
            ap.append(`<p>If there is no class-specific handler, you might try GenericAgent.`);
            ap.modal();
            return;
        } else {
            pop_func = this.constructors[agent_class];
        }

        // Get a unique id - this will be the base ID for all the
        // controls in the tab.
        var uid = 'ocs'+(this._next_id++);

        // Create new div and add it to the tab registry.
        dest_div_id = `${uid}-tab`;
        var div = $('#tabs').append(`<div id="${dest_div_id}" class="ocs_tab">`);
        var destructor = pop_func($('#'+dest_div_id), uid, args);
        $(`<li><a id="${uid}-tab-link" href='#${dest_div_id}'>${name}</a><span id="${uid}-closer">` +
          `<i class="fa fa-window-close"></i></span></li>`)
            .appendTo("#tabs .ui-tabs-nav");
        $('#tabs').tabs( "refresh" );

        // Mark the tab clearly if agent connection drops.
        ocs_connection.agent_list.subscribe(uid + '-tab', args.address, function (addr, ok) {
            var el = $('#' + uid + '-tab-link');
            if (ok)
                el.removeClass('ocs_missing_agent');
            else
                el.addClass('ocs_missing_agent');
        });

        var tabman = this;
        $('#' + uid + '-closer')
            .on('click', () => tabman.del(uid))
            .addClass('obviously_clickable');
        this.ui_reg[name] = {'base_id': uid, 'div_id': dest_div_id,
                          'destructor': destructor};
        return this.ui_reg[name];
    }

    this.activate = function(base_id) {
        // This seems to be the most reliable.
        $('#' + base_id + '-tab-link').trigger('click');
    }

    this.del = function(base_id) {
        /* Tear down the tab specified by base_id.  This will remove
         * the tab from the document tree and also call the destructor
         * function for that UI. */
        ocs_connection.agent_list.unsubscribe(base_id + '-tab');

        // Un-tab...
        var tabIdStr = '#'+base_id+'-tab';
        $(tabIdStr).remove();
        var hrefStr = "a[href='" + tabIdStr + "']"
        $(hrefStr).closest("li").remove()
        $('#tabs').tabs("refresh");
        // Pop from registry and call destructors.
        var reg = this.ui_reg;
        $.each(reg, function (key, val) {
            if (val.base_id == base_id) {
                delete reg[key];
                if (val.destructor)
                    val.destructor();
            }
        });
    }
}


function OcsUiHelper(base_id, client) {
    /* OcsUiHelper: help construct UI elements for Agent control and
     * monitoring.  Instantiate with the base_id that should be used
     * to prefix all element ids, and with an AgentClient that should
     * be used for method calls. */

    this.base_id = base_id;
    this.client = client;

    /* input_registry is a map from op_name to input list
     * objects. Each input list object maps simple input name
     * (e.g. delay) to an element id, e.g. "ocs101-delay_task-delay".
     * This is used to find input element ids by knowing only
     * ('delay_task', 'delay').
    */
    this.input_registry = {};

    // auto_boxes determines whether each operation's controls get a
    // border.
    this.auto_boxes = true;
}

OcsUiHelper.prototype = {
    dest: function(elem) {
        // @param (Object) elem : The target element, probably a
        // $('<div>'),

        this.base_e = elem;
        this.e = null;
        return this;
    },

    set_boxes: function(auto_boxes) {
        this.auto_boxes = auto_boxes;
        if (!auto_boxes) {
            var x = $('<div class="box">');
            this.e = $('<form class="ocs_ui">');
            x.append(this.e);
            this.base_e.append(x);
        }
        return this;
    },

    _next_e: function() {
        if (this.auto_boxes) {
            var x = $('<div class="box">').appendTo(this.base_e);
            this.e = $('<form class="ocs_ui">').appendTo(x);
        }
    },

    /* Panel declarations
     *
     * Inputs and indicators need to be grouped within a named
     * mini-panel, either associated with a task or process (task()
     * and process()) or unassociated (panel()).
     */

    set_context: function(op_name, op_type) {
        // Start a new mini-panel with the specified op_name, and of
        // the specified op_type ('task', 'process', or null).
        this._next_e();
        if (!op_name)
            op_name = '';
        this.op_name = op_name;
        this.op_type = op_type;
        this.input_registry[this.op_name] = {};
        return this;
    },

    task: function(op_name) {
        // Start a new mini-panel, in this case for a Task.
        return this.set_context(op_name, 'task');
    },

    process: function(op_name) {
        // Start a new mini-panel, in this case for a Process.
        return this.set_context(op_name, 'process');
    },

    /* Passive */

    banner: function(label_text) {
        /* bold label_text as an h2, spanning (up to) the full width. */
        this.e.append(`<h2 class="ocs_triple ocs_banner">${label_text}`);
        return this;
    },

    /* Inputs */

    op_header: function(opts) {
        /* bold op_name followed by start / stop buttons.  If opts is
         * passed in, it may contain:
         * 
         * - client: An AgentClient to use for start/stop methods.
             Overrides this.client.
         */
        var id_base = this.base_id + '-' + this.op_name;
        var op_name = this.op_name;
        var client = this.client;
        if (opts && opts.client)
            client = opts.client;
        if (this.op_type == 'task') {
            this.e.append($(`<label class="important">${this.op_name}</label>`
                            +`<input id="${id_base}-start" type="button" value="Start" />`
                            +'<span />'
                            //+`<input id="${id_base}-abort" type="button" value="Abort" disabled />`
                           ));
            if (client) {
                this.on(op_name, 'start', (params) => client.start_task(op_name, params));
                //this.on(op_name, 'abort', () => client.abort_task(op_name));
            }
        } else if (this.op_type == 'process') {
            this.e.append($(`<label class="important">${this.op_name}</label>`
                            +`<input id="${id_base}-start" type="button" value="Start" />`
                            +`<input id="${id_base}-stop" type="button" value="Stop" />`));
            if (client) {
                this.on(op_name, 'start', (params) => client.start_proc(op_name, params));
                this.on(op_name, 'stop', () => client.stop_proc(op_name));
            }
        } else {
            this.e.append($(`<div>`)).append($(`<div>`));
        }
        return this;
    },

    text_input: function(_id, label_text) {
        /* A wide input box, with label_text. */
        var input_id = this.base_id + '-' + this.op_name + '-' + _id;
        this.e.append($(`<label>${label_text}</label>` +
                        `<input class="ocs_double" type="text" id="${input_id}" />`));
        this.input_registry[this.op_name][_id] = input_id;
        return this;
    },

    dropdown: function(_id, label_text, options) {
        var input_id = this.base_id + '-' + this.op_name + '-' + _id;
        var use_val_as_key = Array.isArray(options);
        this.e.append($(`<label>${label_text}</label>` +
                        `<select class="ocs_double ocs_ui" id="${input_id}">`));
        $.each(options, function (key, val) {
            if (use_val_as_key)
                key = val;
            $('#' + input_id).append(`<option value="${key}">${val}</option>`);
        });
        this.input_registry[this.op_name][_id] = input_id;
        return this;
    },

    /* Indicators */

    indicator: function(_id) {
        /* A full width div, for whatever. */
        var ind_id = this.base_id + '-' + this.op_name + '-' + _id;
        this.e.append($(`<div class="ocs_triple" id="${ind_id}"/>`));
        return this;
    },

    text_indicator: function(_id, label_text, opts) {
        /* A wide indicator text box, with label_text. */
        var ind_id = this.base_id + '-' + this.op_name + '-' + _id;
        this.e.append($(`<label>${label_text}</label>` +
                        `<input class="ocs_double" type="text" id="${ind_id}" readonly />`));
        if (!opts)
            opts = {};
        if (opts.center)
            $('#' + ind_id).css('text-align', 'center');
        return this;
    },

    status_indicator: function() {
        /* A special text_indicator for operation status.  Likely
         * enrichened with some sort of bell or whistle. */
        var ind_id = this.base_id + '-' + this.op_name + '-status';
        this.e.append($(`<label>Status:` +
                        `<i class="fa fa-spinner operation_icon" id="${ind_id}-spinner"></i>` +
                        `</label>` +
                        `<input class="ocs_double" type="text" id="${ind_id}" readonly />`
                        ));
        return this;
    },

    progressbar: function(_id, label_text) {
        /* A progressbar indicator, with label_text. */
        var ind_id = this.base_id + '-' + this.op_name + '-' + _id;
        var span_class = 'ocs_triple';
        if (label_text) {
            span_class = 'ocs_double';
            this.e.append(`<label>${label_text}</label>`);
        }
        var pb = $(`<div id="${ind_id}">`).addClass(span_class);
        pb.progressbar({value: 0.});
        this.e.append(pb);
        return this;
    },

    canvas: function(_id) {
        /* A canvas element, spanning full width. */
        var ind_id = this.base_id + '-' + _id;
        this.e.append($(`<canvas class="ocs_triple autopop_box" id="${ind_id}" />`));
        return this;
    },


    /* Functions below this point are used after the UI has been
     * constructed. */

    _get_inputs: function(op_name) {
        /* Retrieve the input data associated with the specified
         * operation and return it as an object with simple field
         * names. */
        data = {};
        $.each(this.input_registry[op_name], function(key, value) {
            var input_id = value; //this.base_id + '-' + op_name + '-' + key;
            data[key] = $('#' + input_id).val();
        });
        return data;
    },

    on: function(op_name, action, callback, reset=false) {
        /* Assign an event handler to a button (probably one from
         * op_header). */
        var ui = this;
        var input_id = this.base_id + '-' + op_name + '-' + action;
        if (reset)
            $('#' + input_id).off('click');
        $('#' + input_id).on('click', function() {
            data = ui._get_inputs(op_name);
            callback(data);
        });
    },

    set_status: function(op_name, session) {
        /* Update the status_indicator associated with op_name.  The
         * status passed in should be a session object returned from
         * AgentClient.  */
        var input_id = this.base_id + '-' + op_name + '-status';
        var ago = timestamp_now() - session.start_time;
        var t = '(unknown)';
        switch(session.status) {
        case 'idle':
        case 'starting':
        case 'running':
            t = session.status + ' (' + human_timespan(ago, 1) + ')';
            break;
        case 'done':
            var ago = timestamp_now() - session.end_time;
            var success = {true: 'OK', false: 'ERROR'}[session.success];
            t = `${session.status} - ${success} - ` + human_timespan(ago, 1) + ' ago';
            break;
        }
        $('#' + input_id).val(t);
        var spnr = $('#' + input_id + '-spinner');
        if (session.status == 'running')
            spnr.addClass('spinning');
        else
            spnr.removeClass('spinning');
    },

    set_connection_status(op_name, ind_id, ok, opts) {
        var el = this.get(op_name, ind_id);
        if (ok) {
            el.val('connection ok').removeClass('ocs_missing_agent')
        } else {
            el.val('CONNECTION LOST').addClass('ocs_missing_agent');
        }
        if (opts.input_containers) {
            $.each(opts.input_containers, function (i, _id) {
                $('#' + _id + ' input').prop('disabled', !ok);
                if (!ok)
                    $('#' + _id + ' i').removeClass('spinning');
            });
        }
    },

    get: function(op_name, ind_id) {
        /* Get the element id of the named indicator. */
        return $('#' + this.base_id + '-' + op_name + '-' + ind_id);
    },
}
