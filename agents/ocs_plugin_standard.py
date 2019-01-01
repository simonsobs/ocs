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
        ('Lakeshore372Agent', 'thermometry/LS372_agent.py'),
        ('Lakeshore240Agent', 'thermometry/LS240_agent.py'),
        ('SmurfAgent', 'smurf/Smurf_Agent.py'),
        ('HostMaster', 'host_master/host_master.py'),
]:
    ocs.site_config.register_agent_class(n, os.path.join(root, f))
