"""
Register our agents in ocs central.  In order for this script to
be imported by site_config.scan_for_agents(), it must be in the python
path and called something like ocs_plugin_*.
"""

import ocs
import os
root = os.path.abspath(os.path.split(__file__)[0])

for n, f in [
        ('RegistryAgent', 'registry/agent.py'),
        ('AggregatorAgent', 'aggregator/agent.py'),
        ('HostManager', 'host_manager/agent.py'),
        ('FakeDataAgent', 'fake_data/agent.py'),
        ('InfluxDBAgent', 'influxdb_publisher/agent.py'),
        ('BarebonesAgent', 'barebones/agent.py'),
]:
    ocs.site_config.register_agent_class(n, os.path.join(root, f))
