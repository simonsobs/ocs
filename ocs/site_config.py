import ocs

import shutil
import socket
import os
import sys
import yaml
import argparse
import collections
import deprecation


class SiteConfig:
    def __init__(self):
        self.hosts = {}
        self.hub = None
        self.source_file = None

    @classmethod
    def from_dict(cls, data):
        """Args:
            data: The configuration dictionary.

        The configuration dictionary should have the following elements:

        ``hub`` (required)
            Describes what WAMP server and realm Agents and Clients
            should use.

        ``hosts`` (required)
            A dictionary of HostConfig descriptions.  The keys in this
            dictionary can be real host names on the network,
            pseudo-host names, or the special value "localhost".

        A HostConfig marked for "localhost" will match any host that
        does not have an exact match in the hosts dictionary.  This
        should normally be used only in single-host test systems or
        examples.

        Client programs will normally (i.e., by default) try to load
        the HostConfig associated with the system hostname (that which
        is returned by socket.gethostname()). But this can be
        overridden easily, for example by using the ``--site-host``
        command line argument.  It is thus quite reasonable to use the
        hosts dictionary to hold a set of useful configurations
        indexed by a user-specified string (a pseudo-host).

        """
        self = cls()
        hosts = data.get('hosts')
        if hosts:
            for k, v in hosts.items():
                assert (k not in self.hosts)  # duplicate host name in config file!
                self.hosts[k] = HostConfig.from_dict(v, parent=self, name=k)
        self.hub = HubConfig.from_dict(data['hub'], parent=self)
        return self

    @classmethod
    def from_yaml(cls, filename):
        filename = os.path.abspath(filename)
        with open(filename) as f:
            data = yaml.safe_load(f)
        self = cls.from_dict(data)
        self.source_file = filename
        return self


class HostConfig:
    def __init__(self, name=None):
        self.instances = []
        self.name = name
        self.agent_paths = []
        self.log_dir = None
        self.working_dir = os.getcwd()
        self.crossbar_timeout = None

    @classmethod
    def from_dict(cls, data, parent=None, name=None):
        """Args:
            data: The configuration dictionary.
            parent: the SiteConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:

        ``agent-instances`` (required)
            A list of AgentConfig descriptions.

        ``agent-paths`` (optional)
            A list of additional paths where OCS is permitted to
            search for Agent plugin modules.

        ``crossbar`` (optional)
            Settings to assist with starting / stopping / monitoring a
            crossbar server running on this host.  There is a single
            crossbar server for an OCS network and thus this entry
            should be defined for at most one of the hosts in the site
            config file.  Note that setting this to None (or null)
            will disable host crossbar control, while setting it to an
            empty dictionary, {}, will enable local host crossbar
            control with default settings.

        ``log-dir`` (optional)
            Path at which to write log files.  Relative paths will be
            interpreted relative to the "working directory"; see
            --working-dir command line option.
        """
        self = cls(name=name)
        self.parent = parent
        self.data = data
        self.instances = data['agent-instances']
        self.agent_paths = data.get('agent-paths', [])
        self.crossbar = CrossbarConfig.from_dict(data.get('crossbar'))
        self.log_dir = data.get('log-dir', None)
        self.crossbar_timeout = data.get('crossbar_timeout', 10)
        return self


class CrossbarConfig:
    @classmethod
    def from_dict(cls, data, parent=None):
        """Args:
            data: The configuration dictionary, or None.
            parent: the HostConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:

        ``config-dir`` (optional): Location of crossbar config.json;
            this gets passed to ``--cbdir``, if specified..

        ``bin`` (optional): The path to the crossbar executable.
            This defaults to shutil.which('crossbar').

        If data is None, returns None.  Otherwise returns a
        CrossbarConfig object.
        """
        if data is None:
            return None
        self = cls()
        self.parent = parent
        self.binary = data.get('bin', shutil.which('crossbar'))
        self.cbdir = data.get('config-dir')
        if self.cbdir is None:
            self.cbdir_args = []
        else:
            self.cbdir_args = ['--cbdir', self.cbdir]
        return self

    def get_cmd(self, cmd):
        if self.binary is None:
            raise RuntimeError("Crossbar binary could not be found in PATH; "
                               "specify the binary in site_config?")
        if not os.path.exists(self.binary):
            raise RuntimeError("The crossbar binary specified in site_config "
                               "does not seem to exist: %s" % self.binary)
        return [self.binary, cmd] + self.cbdir_args

    def summary(self):
        return summarize_dict({
            'bin': self.binary,
            'config-dir': self.cbdir,
        })


class HubConfig:
    @classmethod
    def from_dict(cls, data, parent=None):
        """Args:
            data: The configuration dictionary.
            parent: the SiteConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:

        ``wamp_server`` (required): URL to the WAMP router's websocket
            access point for ocs.  E.g., ``ws://host-2:8001/ws``.
            WAMP routers can have multiple access points, with
            different protocols, security layers, and permissions.
            (Command line override: ``--site-hub``.)

        ``wamp_http`` (optional): URL to the WAMP router's http bridge
            interface.  This is the best interface for simple clients
            to use.  E.g., ``http://host-2:8001/call``.

        ``wamp_realm`` (required): The WAMP realm to use.  WAMP
            clients operating in a particular realm are isolated from
            clients connected to other realms.  Example and test code
            will often use ``debug_realm`` here.  (Command line
            override: ``--site-realm``.)

        ``address_root`` (required): The base address to be used by
            all OCS Agents.  This is normally something simple like
            ``observatory`` or ``detlab``.  (Command line override:
            ``--address-root``.)

        """
        self = cls()
        self.parent = parent
        self.data = data
        return self

    def summary(self):
        return summarize_dict(self.data)


class InstanceConfig:

    _MANAGE_MAP = {
        # Fundamental states
        'host/up': 'host/up',
        'host/down': 'host/down',
        'docker/up': 'docker/up',
        'docker/down': 'docker/down',
        'ignore': 'ignore',

        # Aliases for deprecated yes / no.
        'yes': 'host/up',
        'no': 'ignore',

        # Non-deprecated aliases.
        'docker': 'docker/up',
        'host': 'host/up',
        'up': 'host/up',
        'down': 'host/down',

        # Default.
        None: 'host/up',
    }

    def __init__(self):
        self.arguments = []

    @classmethod
    def from_dict(cls, data, parent=None):
        """Args:
            data: The configuration dictionary.
            parent: the HostConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:

        ``instance-id`` (str, required)
            This string is used to set the Agent instance's base
            address.  This may also be matched against the instance-id
            provided by the Agent instance, as a way of finding the
            right InstanceConfig.

        ``agent-class`` (str, optional)
            Name of the Agent class.  This
            may be matched against the agent_class name provided by
            the Agent instance, as a way of finding the right
            InstanceConfig.

        ``arguments`` (list, optional):
            A list of arguments that should be passed back to the
            agent.  Historically the arguments have been grouped into
            into key value pairs, e.g. [['--key1', 'value'],
            ['--key2', 'value']] but these days whatever you passed in
            gets flattened to a single list (i.e. that is equivalent
            to ['--key1', 'value', '--key2', 'value'].

        ``manage`` (str, optional):
            A string describing how a HostManager should manage this
            agent.  See notes.

        Notes:

            The ``manage`` value is only relevant if a HostManager is
            configured to operate on the host.  In that case, the
            HostManager's treatment of the agent instance depends on
            the value of ``manage``:

            - "ignore": HostManager will not attempt to manage the
              agent instance.
            - "host/up": HostManager will manage the agent instance,
              launching it on the host system.  On startup, the
              instance will be set to target_state "up" (i.e. the
              HostManager will try to start it).
            - "host/down": like host/up, but HostManager will not
              start up the agent instance until explicitly requested
              to do.
            - "docker/up": HostManager will manage the agent instance
              through Docker.  On Startup, the instance will be set to
              target_state "up".
            - "docker/down": Like docker/up, but the instance will be
              forced to target_state "down" on startup.

            In earlier versions of OCS, the acceptable values were
            "yes", "no", and "docker".  Those were equivalent to
            current values of "host/down", "ignore", and "docker/down".

            Those values are still accepted, but note that "yes" and
            "docker" are now equivalent to "host/up" and "docker/up".

            The following abbreviated values are also accepted:

            - "host": same as "host/up"
            - "up": same as "host/up"
            - "down": same as "host/down"

        """
        self = cls()
        self.parent = parent
        self.data = data
        self.arguments = self.data.get('arguments', [])
        self.manage = self.data.get('manage')
        self.manage = self._MANAGE_MAP.get(self.manage, self.manage)
        return self


def summarize_dict(d):
    output = '\n'.join(['  %s: %s,' % (repr(k), repr(v))
                        for k, v in d.items()])
    return '{\n%s\n}' % output


class ArgContainer:
    """
    A container to store a list of args as a dictionary, with the argument names
    (beginning with a hyphen) as keys, and list of arguments as values. Any
    arguments passed before an argument key is put under the '__positional__'
    key, even though positional arguments aren't really supported by ocs agents
    or the site-config....

    Args:
        args (list):
            Argument list (each item should be a single word)

    Attributes:
        arg_dict (dict):
            Dictionary of arguments, indexed by argument keyword.
    """

    def __init__(self, args):
        self.arg_dict = collections.OrderedDict()

        cur_key = '__positional__'
        self.arg_dict[cur_key] = []

        def is_new_arg(arg):
            if arg[0] != '-':
                return False
            # Check that first character after '-' is not a digit
            if not arg.strip('-')[0].isalpha():
                return False
            return True

        for arg in args:
            if is_new_arg(arg):
                cur_key = arg
                self.arg_dict[cur_key] = []
            else:
                self.arg_dict[cur_key].append(arg)

    def update(self, arg_container2):
        """
        Updates the arg_dict with the arg_dict from another ArgContainer

        Args:
            arg_container2 (ArgContainer):
                The other ArgContainer with which you want to update the arg_dict.
        """
        self.arg_dict.update(arg_container2.arg_dict)

    def to_list(self):
        """
        Returns the argument list representation of this container.
        """
        arg_list = []
        for k, v in self.arg_dict.items():
            if k != '__positional__':
                arg_list.append(k)
            arg_list.extend(v)

        return arg_list


def add_arguments(parser=None):
    """
    Add OCS site_config options to an ArgumentParser.

    Args:
        parser: an ArgumentParser.  If this is None, a new parser is
            created.

    Returns:
        The ArgumentParser that was passed in, or the new one.

    Arguments include the ``--site-*`` family.  See code or online
    documentation for details.
    """
    # Note that we use sphinxarg.ext to expose the help=... text in
    # the online sphinx docs.

    """
    ``--site=...``
        Instead of the default site, use the configuration
        for the specified site.  The configuration is loaded from
        ``$OCS_CONFIG_DIR/{site}.yaml``.  If --site=none, the
        site_config facility will not be used at all.

    ``--site-file=...``
        Instead of the default site config, use the
        specified file.  Full path must be specified.

    ``--site-host=...``
        Override the OCS determination of what host this instance is
        running on, and instead use the configuration for the
        indicated host.

    ``--site-hub=...``:
        Override the ocs hub url (wamp_server).

    ``--site-http=...``:
        Override the ocs hub http url (wamp_http).

    ``--site-realm=...``:
        Override the ocs hub realm (wamp_realm).

    ``--instance-id=...``:
        Look in the SCF for Agent-instance specific configuration
        options, and use those to launch the Agent.

    ``--address-root=...``:
        Override the site default address root.

    ``--log-dir=...``:
        Override the host default logging directory.

    ``--working-dir=...``:
        Propagate the working directory.

    ``--crossbar-timeout=...``:
        Length of time in seconds that the Agent will try to reconnect to the
        crossbar server before shutting down.

    """
    if parser is None:
        parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Site Config Options')
    group.add_argument('--site', help="Instead of the default site, use the "
                       "configuration for the specified site.  The configuration is loaded "
                       "from ``$OCS_CONFIG_DIR/{site}.yaml``.  If ``--site=none``, the "
                       "site_config facility will not be used at all.")
    group.add_argument('--site-file', help="Instead of the default site config, "
                       "use the specified file. Full path must be specified.")
    group.add_argument('--site-host', help="Override the OCS determination of "
                       "what host this instance is running on, and instead use the "
                       "configuration for the indicated host.")
    group.add_argument('--site-hub', help="Override the ocs hub url (wamp_server).")
    group.add_argument('--site-http', help="Override the ocs hub http url (wamp_http).")
    group.add_argument('--site-realm', help="Override the ocs hub realm (wamp_realm).")
    group.add_argument('--instance-id', help="Look in the SCF for "
                       "Agent-instance specific configuration options, and use those to launch "
                       "the Agent.")
    group.add_argument('--address-root', help="Override the site default address root.")
    group.add_argument('--registry-address', help="Deprecated.")
    group.add_argument('--log-dir', help="Set the logging directory.")
    group.add_argument('--working-dir', help="Propagate the working directory.")
    group.add_argument('--crossbar-timeout', type=int, help="Length of time in seconds "
                       "that the Agent will try to reconnect to the crossbar server before "
                       "shutting down. Note this is set per Agent in an instance's arguments list.")
    return parser


def get_config(args, agent_class=None):
    """
    Args:
        args: The argument object returned by
            ArgumentParser.parse_args(), or equivalent.  It is assumed
            that all properties defined by "add_arguments" are present
            in this object.
        agent_class: Class name passed in to match against the list of
            device classes in each host's list.

    Special values accepted for agent_class:
    - '*control*': do not insist on matching host or device.
    - '*host*': do not insist on matching device (but do match host).

    Returns:
        The tuple (site_config, host_config, device_config).
    """
    if args.site == 'none':
        return (None, None, None)

    site_file = args.site_file
    site = args.site
    if site_file is None:
        if site is None:
            site = 'default'
        assert (os.getenv('OCS_CONFIG_DIR') is not None)
        site_file = os.path.join(os.getenv('OCS_CONFIG_DIR'),
                                 site + '.yaml')
    else:
        assert (site is None)  # do not pass both --site and --site-file

    # Load the site config file.
    site_config = SiteConfig.from_yaml(site_file)

    # Matching behavior.
    no_host_match = (agent_class == '*control*')
    no_dev_match = no_host_match or (agent_class == '*host*')

    # Identify our host and update site.hub.
    host_config = None
    if args.site_host is not None:
        host_attempts = [args.site_host, 'localhost']
    else:
        host_attempts = [socket.gethostname(), 'localhost']
    for host_try in host_attempts:
        if host_try in site_config.hosts:
            host_config = site_config.hosts[host_try]
            host_update_dict = {
                k: host_config.data[k]
                for k in ['wamp_server', 'wamp_http', 'wamp_realm']
                if k in host_config.data.keys()
            }
            site_config.hub.data.update(host_update_dict)
            # Updates host_config with command line args
            if args.working_dir is not None:
                host_config.working_dir = args.working_dir
            if args.log_dir is not None:
                host_config.log_dir = args.log_dir
            break
    else:
        if not no_host_match:
            raise KeyError('Site config has no entry in "hosts" for {}'
                           .format(host_attempts))

    # Override the WAMP hub?
    if args.site_hub is not None:
        site_config.hub.data['wamp_server'] = args.site_hub

    if args.site_http is not None:
        site_config.hub.data['wamp_http'] = args.site_http

    # Override the realm?
    if args.site_realm is not None:
        site_config.hub.data['wamp_realm'] = args.site_realm

    # Identify our agent-instance.
    instance_config = None
    if no_dev_match:
        pass
    elif args.instance_id is not None:
        # Find the config for this instance-id.
        for dev in host_config.instances:
            if dev['instance-id'] == args.instance_id:
                instance_config = InstanceConfig.from_dict(
                    dev, parent=host_config)
                break
    else:
        # Use the agent_class to figure it out...
        for dev in host_config.instances:
            if dev['agent-class'] == agent_class:
                if instance_config is not None:
                    raise RuntimeError(
                        f"Multiple matches found for agent-class={agent_class}"
                        " ... you probably need to pass --instance-id=")
                instance_config = InstanceConfig.from_dict(
                    dev, parent=host_config)
    if instance_config is None and not no_dev_match:
        raise RuntimeError("Could not find matching device description.")
    return collections.namedtuple('SiteConfig', ['site', 'host', 'instance'])(site_config, host_config, instance_config)


def add_site_attributes(args, site, host=None):
    """
    Adds site and host attributes to namespace if they do not exist.

    Args:
        args:
            namespace to add attributes to.
        site:
            Site config object.
        host:
            Host config object.
    """
    if args.site_hub is None:
        args.site_hub = site.hub.data['wamp_server']
    if args.site_http is None:
        args.site_http = site.hub.data.get('wamp_http')
    if args.site_realm is None:
        args.site_realm = site.hub.data['wamp_realm']
    if args.address_root is None:
        args.address_root = site.hub.data['address_root']
    if (args.log_dir is None) and (host is not None):
        args.log_dir = host.log_dir
    if (args.crossbar_timeout is None) and (host is not None):
        args.crossbar_timeout = host.crossbar_timeout


@deprecation.deprecated(deprecated_in='v0.6.0',
                        details="Use site_config.parse_args instead")
def reparse_args(args, agent_class=None):
    """
    THIS FUNCTION IS NOW DEPRECATED... Use the parse_args function instead
    to parse command line and site-config args simultaneously.

    Process the site-config arguments, and modify them in place
    according to the agent-instance's computed instance-id.

    Args:
        args: The argument object returned by
            ArgumentParser.parse_args(), or equivalent.

        agent_class: Class name passed in to match against the list of
            device classes in each host's list.

    Special values accepted for agent_class:
    - '*control*': do not insist on matching host or device.
    """
    if args.site == 'none':
        return args

    site, host, instance = get_config(args, agent_class=agent_class)

    add_site_attributes(args, site, host=host)

    if instance is not None:
        if args.instance_id is None:
            args.instance_id = instance.data['instance-id']

        for k, v in instance.data['arguments']:
            kprop = k.lstrip('-').replace('-', '_')
            print('site_config is setting values of "%s" to "%s".' % (kprop, v))
            setattr(args, kprop, v)

    return args


def get_control_client(instance_id, site=None, args=None, start=True,
                       client_type='http'):
    """Instantiate and return a client_http.ControlClient, targeting the
    specified instance_id.

    Args:
        site (SiteConfig): All configuration will be taken from this
            object, if it is not None.

        args: Arguments from which to derive the site configuration.
            If this is None, then the arguments from the command line
            are parsed through the usual site_config system.  If this
            is a list of strings, then these arguments will be parsed
            instead of sys.argv[1:].  Note that to use the default
            configuration (without looking at sys.argv), pass args=[].
            It is also permitted to pass a pre-parsed
            argparse.Namespace object (or similar).

        start (bool): Determines whether to call .start() on the client before
            returning it.

        client_type (str): Select the client type, currently only 'http'.
            wamp_http address must be known. Note that 'wampy' used to be a
            supported type, but was dropped in OCS v0.8.0.

    Returns a ControlClient.

    """
    if site is None:
        if args is None:
            args = sys.argv[1:]
        if not hasattr(args, 'instance_id'):
            # If it doesn't have .instance_id, it's not a parsed
            # Namespace so let's assume it's a list of strings.
            args = ocs.site_config.parse_args(agent_class='*control*',
                                              args=args)
        site, _, _ = ocs.site_config.get_config(args, '*control*')
    full_addr = '%s.%s' % (site.hub.data['address_root'], instance_id)
    if client_type is None:
        if site.hub.data.get('wamp_http'):
            client_type = 'http'
        else:
            client_type = 'wampy'
    if client_type == 'wampy':
        raise ValueError('client_type %s no longer supported' % client_type)
    elif client_type == 'http':
        from ocs import client_http
        client = client_http.ControlClient(
            full_addr,
            url=site.hub.data['wamp_http'],
            realm=site.hub.data['wamp_realm'])
    else:
        raise ValueError('Unknown client_type request: %s' % client_type)
    return client


# We'll also keep the Agent script registry here.
agent_script_reg = {}


def register_agent_class(class_name, filename):
    """Register an Agent script in the site_config registry.

    Args:
        class_name (str): The Agent class name, e.g. "HostManager".
        filename (str): The full path to the script that launches an
            instance of this Agent class.

    """
    agent_script_reg[class_name] = filename


def scan_for_agents(do_registration=True):
    """Identify and import ocs Agent plugin scripts.  This will find all
    modules in the current module search path (sys.path) that begin
    with the name 'ocs_plugin\\_'.

    Args:
        do_registration (bool): If True, the modules are imported,
            which likely causes them to call register_agent_class on
            each agent they represent.

    Returns:
        The list of discovered module names.

    """
    import pkgutil
    import importlib
    items = []
    for modinfo in pkgutil.iter_modules():
        if modinfo.name.startswith('ocs_plugin_'):
            items.append(modinfo.name)
            if do_registration:
                importlib.import_module(modinfo.name)
    return items


def parse_args(agent_class=None, parser=None, args=None):
    """
    Function to parse site-config and agent arguments. This function takes
    site, host, and instance arguments into account by making sure the instance
    arguments get passed through the arg_parse parser. This helps make sure
    units and options are consistent with those defined by the argparse
    argument, even when the arguments come from the site-config file and not
    the command line.

    Args:
        agent_class (str, optional):
            Name of the Agent class.  This
            may be matched against the agent_class name provided by
            the Agent instance, as a way of finding the right
            InstanceConfig.
        parser (argparse.ArgumentParser, optional):
            Argument parser containing agent-specific arguments.
            If None, an empty parser will be created.
        args (list of str):
            Arguments to parse; defaults to sys.argv[1:].

    Returns:
        An argparse.Namespace, as you would get from
        parser.parse_args().

    """

    # Creates pre_parser
    pre_parser = argparse.ArgumentParser()
    add_arguments(pre_parser)

    # Full parser
    if parser is None:
        parser = argparse.ArgumentParser()
    add_arguments(parser)

    if args is None:
        args = sys.argv[1:]

    # Intercepts help commands to print full usage statement
    if any(h in args for h in ['-h', '--help']):
        # Instead of print_help(), trust parse_args() to run resolve
        # to any sub-parsers and print context-appropriate help.
        parser.parse_args(args=args)
        parser.exit()  # shouldn't get here.

    pre_args, _ = pre_parser.parse_known_args(args=args)

    site, host, instance = get_config(pre_args, agent_class=agent_class)

    if instance is not None:
        # When the user omits instance_id, it can still be matched,
        # through agent_class by the get_config parser.  In that case,
        # copy its value into args.
        if pre_args.instance_id is None:
            instance.arguments.append(['--instance-id',
                                       instance.data['instance-id']])

    # Container from command line args
    cl_container = ArgContainer(args)

    # Flattens instance arguments to single non-nested list
    def flatten(container):
        out = []
        for i in container:
            if isinstance(i, (list, tuple)):
                out.extend(flatten(i))
            else:
                out.append(i)
        return out

    arg_container = ArgContainer([])

    if instance is not None:
        arg_container.update(ArgContainer(map(str, flatten(instance.arguments))))

    # Replace site values with command line values if they exist
    arg_container.update(cl_container)

    # Parse combined CL + site arguments
    args = parser.parse_args(args=arg_container.to_list())

    # Add site and host attributes to args namespace
    add_site_attributes(args, site, host=host)

    # Add agent_class attribute.
    if not hasattr(args, 'agent_class'):
        setattr(args, 'agent_class', agent_class)

    return args
