from ocs.agents import ocs_plugin_standard


def test_agent_script_reg():
    reg = ocs_plugin_standard.ocs.site_config.agent_script_reg
    print(reg)
    assert reg != {}
