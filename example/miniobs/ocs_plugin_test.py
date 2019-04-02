"""
Register our FakeDataAgent launcher script.
"""

import ocs
import os
root = os.path.abspath(os.path.split(__file__)[0])
ocs.site_config.register_agent_class(
    'FakeDataAgent', os.path.join(root, 'fake_data_agent.py'))
