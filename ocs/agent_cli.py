import argparse
import importlib
import os
import sys
import warnings

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from ocs import site_config

DESCRIPTION = """
This script provides a quick way to start an OCS Agent. You will need to set
OCS_CONFIG_DIR environment variable to the directory containing default.yaml,
or else use ``--site-*`` options to specify your configuration.

To start an Agent, run::

  %(prog)s --instance-id INSTANCE_ID

``ocs-agent-cli`` will also inspect environment variables for commonly passed
arguments to facilitate configuration within Docker containers. Supported
arguments include, ``--instance-id`` as ``INSTANCE_ID``, ``--site-hub`` as
``SITE_HUB``, and ``--site-http`` as ``SITE_HTTP``.

"""


def _get_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)

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
    print(discovered_plugins)
    agents = {}
    for name in discovered_plugins.names:
        (plugin, ) = discovered_plugins.select(name=name)
        loaded = plugin.load()

        # Remove any duplicate agent classes from newly loaded plugin
        current_agents = set(agents)
        conflicts = current_agents.intersection(set(loaded.agents))
        for con in conflicts:
            warnings.warn(
                f'Found duplicate agent-class {con} provided by {name}. ' +
                f'Using {agents[con]}.')
            del loaded.agents[con]

        agents.update(loaded.agents)

    return agents


def main(args=None):
    # Grab instance-id from ENV for running in Docker
    id_env = os.environ.get("INSTANCE_ID", None)

    # Grab commandline arguments
    if args is None:
        argv = sys.argv[1:]

    # Split and flatten argv list
    _split = [x.split('=') for x in argv]
    argv = [x for y in _split for x in y]

    # Inject ENV based instance-id only if not passed on cli
    if "--instance-id" not in argv:
        argv.extend(["--instance-id", id_env])
        if id_env is None:
            print("--instance-id (or $INSTANCE_ID) not provided. Exiting.")
            sys.exit(1)

    # Inject optional argv from ENV
    optional_env = {"--site-hub": "SITE_HUB" ,
                    "--site-http": "SITE_HTTP"}

    for _arg, _var in optional_env.items():
        set_var = os.environ.get(_var, None)
        if set_var is not None and _arg not in argv:
            argv.extend([_arg, set_var])

    print('ARGS', argv)
    parser = _get_parser()

    # Note this is only used to lookup the agent-class, argv is passed to the
    # agent's entrypoint below when calling start(), which includes injected
    # ENV based arguments.
    args = site_config.parse_args(agent_class='*host*',
                                  parser=parser, args=argv)

    # Determine agent-class from instance-id
    (site_, host_, instance) = site_config.get_config(args)
    agent_class = instance.data['agent-class']

    # Import agent's entrypoint and execute
    agents = build_agent_list()
    agent_info = agents[agent_class]
    _module = agent_info["module"]
    _entry = agent_info.get("entry_point", "main")

    mod = importlib.import_module(_module)
    start = getattr(mod, _entry)  # This is the start function.
    start(argv)  # noqa: F821


if __name__ == '__main__':
    # This __main__ checker allows ocs-agent-cli to be invoked through
    # python -m ocs.agent_cli; this is helpful with, e.g., conda when
    # one is trying to use a particular interpreter and its packages.
    main()
