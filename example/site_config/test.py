from ocs import site_config as sc

parser = sc.add_arguments(None)
parser.add_argument('--serial-number')
parser.add_argument('--mode')

args = parser.parse_args(['--site-file', 'telescope.yaml',
                          '--site-host', 'host-1',
                          '--instance-id', 'thermo1'])

c = sc.get_config(args)

sc.reparse_args(args)

print(args.instance_id, args.serial_number, args.mode)
