"""
Register our agents in ocs central.  In order for this script to
be imported by site_config.scan_for_agents(), it must be in the python
path and called something like ocs_plugin_*.
"""

import ocs
import os
root = os.path.abspath(os.path.split(__file__)[0])
print(root)

for n,f in [
        ('RegistryAgent', 'registry.py'),
        ('AggregatorAgent', 'aggregator_agent.py'),
        ('HostManager', 'host_manager.py'),
        ('FakeDataAgent', 'fake_data_agent.py'),
        ('InfluxDBAgent', 'influxdb_publisher.py'),
        ('BarebonesAgent', 'barebones_agent.py'),
]:
    ocs.site_config.register_agent_class(n, os.path.join(root, f))
