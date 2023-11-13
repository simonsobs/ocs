import argparse
import importlib
import os
import setproctitle
import sys
import warnings

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from ocs import site_config

DESCRIPTION = """
This script provides a quick way to start an OCS Agent. You will need to set
``OCS_CONFIG_DIR`` environment variable to the directory containing
default.yaml, or else use ``--site-*`` options to specify your configuration.

To start an Agent, run::

  ocs-agent-cli --instance-id INSTANCE_ID

``ocs-agent-cli`` will also inspect environment variables for commonly
passed arguments to facilitate configuration within Docker containers.
Those environment variables, if defined and non-trivial, will be
passed to the agent script unless they are overridden explicitly on
the ``ocs-agent-cli`` command line.  The environment variables and
arguments are:

  - ``INSTANCE_ID``, will be the default value for ``--instance-id``
  - ``SITE_HOST``, for ``--site-host``
  - ``SITE_HUB``, for ``--site-hub``
  - ``SITE_HTTP``, for ``--site-http``
  - ``CROSSBAR_TIMEOUT``, for ``--crossbar-timeout``


``ocs-agent-cli`` relies on the Agent being run belonging to an OCS Plugin. If
the Agent is not an OCS Plugin it can be run directly using both the
``--agent`` and ``--entrypoint`` flags. For example::

  ocs-agent-cli --agent my_agent.py --entrypoint main --instance-id my-agent-1

"""


def _get_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Passed through to Agent
    parser.add_argument('--instance-id', default=None, help="Agent unique instance-id. E.g. 'aggregator' or 'fakedata-1'.")
    parser.add_argument('--site-hub', default=None, help="Site hub address.")
    parser.add_argument('--site-http', default=None, help="Site HTTP address.")
    parser.add_argument('--site-host', default=None, help="Declare the host the instance is configured in.")
    # Default set in site_config.py within add_arguments()
    parser.add_argument('--crossbar-timeout', type=int, help="Length of time in seconds "
                        "that the Agent will try to reconnect to the crossbar server before "
                        "shutting down. Disable the timeout by setting to 0.")

    # Not passed through to Agent
    parser.add_argument('--agent', default=None, help="Path to non-plugin OCS Agent.")
    parser.add_argument('--entrypoint', default=None, help="Agent module entrypoint function.")

    return parser


def build_agent_list():
    """Builds a list of all Agents available across all ocs plugins installed
    on the system.

    Note:
        Currently if two plugins provide the same Agent the one loaded first is
        used. This should be improved somehow if we expect overlapping Agents
        to be provided by plugins.

    Examples:
        An example agent list:

        >>> build_agent_list()
        {'RegistryAgent': {'module': 'ocs.agents.registry.agent', 'entry_point': 'main'},
        'AggregatorAgent': {'module': 'ocs.agents.aggregator.agent', 'entry_point': 'main'},
        'HostManager': {'module': 'ocs.agents.host_manager.agent', 'entry_point': 'main'},
        'FakeDataAgent': {'module': 'ocs.agents.fake_data.agent', 'entry_point': 'main'},
        'InfluxDBAgent': {'module': 'ocs.agents.influxdb_publisher.agent', 'entry_point': 'main'},
        'BarebonesAgent': {'module': 'ocs.agents.barebones.agent', 'entry_point': 'main'}}

    Returns:
        dict: Dictionary of available agents, with agent names as the keys, and
        dicts containing the module and entry_point as values.

    """
    discovered_plugins = entry_points(group='ocs.plugins')
    print("Installed OCS Plugins:", [x.name for x in discovered_plugins])
    agents = {}
    for name in discovered_plugins.names:
        (plugin, ) = discovered_plugins.select(name=name)
        try:
            loaded = plugin.load()
        except Exception as e:
            print(f"Could not load plugin: {name}")
            print("  Error:", e)
            continue

        # Remove any duplicate agent classes from newly loaded plugin
        current_agents = set(agents)
        conflicts = current_agents.intersection(set(loaded.agents))
        for con in conflicts:
            warnings.warn(
                f'Found duplicate agent-class {con} provided by {name}. '
                + f'Using {agents[con]}.')
            del loaded.agents[con]

        agents.update(loaded.agents)

    return agents


def main(args=None):
    # Grab commandline arguments
    if args is None:
        args = sys.argv[1:]

    parser = _get_parser()
    # pre_args relevant to ocs-agent-cli, post_args passed to Agent entrypoint
    pre_args, post_args = parser.parse_known_args(args)

    # Required arguments
    if pre_args.instance_id is not None:
        # Re-add instance-id to post_args
        post_args.extend(["--instance-id", pre_args.instance_id])
    else:
        # Grab instance-id from ENV for running in Docker
        id_env = os.environ.get("INSTANCE_ID", None)

        # Inject ENV based instance-id only if not passed on cli
        post_args.extend(["--instance-id", id_env])

        # instance-id is always required
        if id_env is None:
            print("--instance-id (or $INSTANCE_ID) not provided. Exiting.")
            sys.exit(1)

    # Optional arguments
    # Add additional optional arguments by appending to optional_env
    # Format is {"arg name within argparse": "ENVIRONMENT VARIABLE NAME"}
    # E.g. --my-new-arg should be {"my_new_arg": "MY_NEW_ARG"}
    optional_env = {"site_hub": "SITE_HUB",
                    "site_http": "SITE_HTTP",
                    "site_host": "SITE_HOST",
                    "crossbar_timeout": "CROSSBAR_TIMEOUT",
                    }

    for _name, _var in optional_env.items():
        # Args passed on cli take priority
        _arg = vars(pre_args)[_name]
        _flag = f"--{_name}".replace('_', '-')
        if _arg is not None:
            post_args.extend([_flag, str(_arg)])
            continue

        # Get from ENV if not passed w/flag
        set_var = os.environ.get(_var, None)
        if set_var is not None:
            post_args.extend([_flag, set_var])

    print('Args:', post_args)  # mostly to debug, but also useful
    # Handle running agent directly (outside of plugin package)
    if pre_args.agent:
        agent_file = pre_args.agent

        # Entrypoint required if running outside of plugin system
        if pre_args.entrypoint is None:
            print("--entrypoint not provided. Exiting")
            sys.exit(1)

        entrypoint = pre_args.entrypoint

        # Insert agent into path for import
        script_path = os.path.dirname(agent_file)
        sys.path.insert(0, script_path)
        mod = importlib.import_module(os.path.basename(agent_file)[:-3])
    else:
        # Note this is only used to lookup the agent-class, post_args are
        # passed to the agent's entrypoint below when calling start(), which
        # includes injected ENV based arguments.
        args = site_config.parse_args(agent_class='*host*',
                                      parser=None, args=post_args)

        # Determine agent-class from instance-id
        (site_, host_, instance) = site_config.get_config(args)
        agent_class = instance.data['agent-class']

        # Import agent's entrypoint and execute
        agents = build_agent_list()
        agent_info = agents[agent_class]
        _module = agent_info["module"]
        entrypoint = agent_info.get("entry_point", "main")

        mod = importlib.import_module(_module)

        title = f'ocs-agent:{instance.data["instance-id"]}'
        print(f'Renaming this process to: "{title}"')
        setproctitle.setproctitle(title)

    start = getattr(mod, entrypoint)  # This is the start function.
    start(args=post_args)


if __name__ == '__main__':
    # This __main__ checker allows ocs-agent-cli to be invoked through
    # python -m ocs.agent_cli; this is helpful with, e.g., conda when
    # one is trying to use a particular interpreter and its packages.
    main()
