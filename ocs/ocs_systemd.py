#!/usr/bin/env python3

import os
import stat
import sys
from ocs import site_config

"""The idea here is to create a launcher script that will live in the
OCS_CONFIG_DIR directory, and also a minimal systemd script that gets
installed to the system.

The launcher script is helpful for configurability -- for example, to
make use of a non-system Python.  If we accept the usefulness/
necessity of the launcher script, then there is not much reason to
create other communication channels between the systemd service file
and the agent.  (For example, one could imagine setting lots of
environment variables in the service, and having host_manager.py fully
self-configure from those.)

"""

SERVICE_DEFAULT = '/etc/systemd/system/'

SYSTEMD_TEMPLATE = """[Unit]
Description=OCS HostManager{host_detail}

[Service]
ExecStart={cmd}
User={service_user}
Restart=always
RestartSec=10s
{environment_lines}

[Install]
WantedBy=multi-user.target
"""

LAUNCHER_TEMPLATE = """#!{shell}

# This launcher script is for use by systemd; a corresponding systemd
# service file was probably installed to {systemd_dest}.

### Add / modify environment and launch variables here.

SITE_FILE={site_file}
PYTHON={python_bin}

###

${{PYTHON}} -m ocs.agent_cli \\
  --site-file=${{SITE_FILE}} \\
  {host_manager_args}
"""


def get_parser():
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Options specific to systemd service creation')
    group.add_argument('--docker-compose', action='append', default=[])
    # group.add_argument('--host', help=)
    group.add_argument('--shell', help="Override the shell used for the launcher script.")
    group.add_argument('--python-bin', help="Select the Python interpreter with which to launch HostManager.")
    group.add_argument('--launcher-dir', help="Override the directory of the launcher script.")
    group.add_argument('--launcher-script', help="Override the name of the launcher script.")
    group.add_argument('--service-dir', help="Directory to which the .service file will be written; "
                       f"default is {SERVICE_DEFAULT}.")
    group.add_argument('--service-user', help="Override the user under which HostManager agent will be run.")
    group.add_argument('--service-name', help="Override the name of the systemd service.")
    group.add_argument('--service-host', help="Set a hostname to use when generating the service name.")
    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = get_parser()
    args = site_config.parse_args(agent_class='*host*',
                                  parser=parser)
    site, host, _ = site_config.get_config(args, agent_class='*host*')
    assert (host.name is not None)  # It won't be, right?

    # The "hostname" is potentially used for a few things:
    # - to name the service
    # - to name the launcher script
    # - to configure the host-manager
    #
    # It's only sensible to have the launcher script name and host-manager
    # use the same value.  For naming the service, the sensible default is
    # to not include the host name, since a most natural configuration
    # would have just one host-manager on the host.
    #
    # So ... site_config host.name will be used for the
    # launcher/host-manager.  And the service name will default to a
    # hostless version unless args.service_host is passed.

    if args.service_name is None:
        if args.service_host is None:
            args.service_name = 'ocs-hostmanager.service'
        else:
            args.service_name = f'ocs-hostmanager-{args.service_host}.service'
    if args.instance_id is None:
        args.instance_id = f'hm-{host.name}'
    if args.shell is None:
        args.shell = os.environ['SHELL']
    if args.launcher_dir is None:
        args.launcher_dir = os.environ['OCS_CONFIG_DIR']
    if args.launcher_script is None:
        args.launcher_script = os.path.join(args.launcher_dir, f'launcher-{args.instance_id}.sh')
    args.launcher_script = os.path.abspath(args.launcher_script)
    if args.service_user is None:
        args.service_user = os.environ['USER']
    if args.service_dir is None:
        args.service_dir = SERVICE_DEFAULT
    if args.service_name is None:
        args.service_name = f'ocs-{args.instance_id}.service'
    args.systemd_dest = os.path.join(args.service_dir, args.service_name)

    if args.python_bin is None:
        args.python_bin = sys.executable
    if args.site_file is None:
        args.site_file = site.source_file

    host_manager_args = [
        f'--instance-id={args.instance_id}',
        f'--site-host={host.name}',
    ]
    if len(args.docker_compose):
        args.docker_compose = [os.path.abspath(f) for f in args.docker_compose]
        host_manager_args.append('--docker-compose=' + ','.join(args.docker_compose))

    host_detail = ' for %s' % host.name
    systemd_script = SYSTEMD_TEMPLATE.format(
        cmd=args.launcher_script,
        host_detail=host_detail,
        environment_lines='',
        **vars(args))

    launcher_code = LAUNCHER_TEMPLATE.format(
        host_manager_args='  \\\n  '.join(host_manager_args),
        **vars(args))

    print(f'Writing {args.launcher_script} ...')
    open(args.launcher_script, 'w').write(launcher_code)
    os.chmod(args.launcher_script, os.stat(args.launcher_script).st_mode
             | (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    print(f'Writing {args.systemd_dest} ...')
    try:
        open(args.systemd_dest, 'w').write(systemd_script)
    except PermissionError:
        print()
        print(f' -- PermissionError trying to write to {args.systemd_dest}!')
        print()
        print('Re-run the previous command, but with --service-dir=./ to create\n'
              'the service file in the current directory.  Then install it with:')
        print()
        print(f'   sudo cp ./{args.service_name} {args.service_dir}')
        print('   sudo systemctl daemon-reload')
