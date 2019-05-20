"""
Register our agents in ocs central.  In order for this script to
be imported by site_config.scan_for_agents(), it must be in the python
path and called something like ocs_plugin_*.
"""

import ocs
import os
root = os.path.abspath(os.path.split(__file__)[0])

for n,f in [
        ('RegistryAgent', 'registry/registry.py'),
        ('AggregatorAgent', 'aggregator/aggregator_agent.py'),
        ('HostMaster', 'host_master/host_master.py'),
        ('FakeDataAgent', 'fake_data/fake_data_agent.py'),
]:
    ocs.site_config.register_agent_class(n, os.path.join(root, f))
