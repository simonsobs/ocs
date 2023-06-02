from unittest.mock import MagicMock, patch

import pytest
import yaml

from ocs.site_config import (ArgContainer, CrossbarConfig, HostConfig,
                             HubConfig, InstanceConfig, SiteConfig,
                             get_control_client)

# Used for testing all Config objects
HUB_CFG = {'wamp_server': 'ws://127.0.0.1:18001/ws',
           'wamp_http': 'http://127.0.0.1:18001/call',
           'wamp_realm': 'test_realm',
           'address_root': 'observatory'}
CROSSBAR_CFG = {'config-dir': '/simonsobs/ocs/dot_crossbar/',
                'bin': '/path/to/crossbar'}
INSTANCE_CFG = {'agent-class': 'FakeDataAgent',
                'instance-id': 'fake-data1',
                'arguments': ['--mode', 'acq',
                              '--num-channels', '16',
                              '--sample-rate', '5',
                              '--frame-length', '10'],
                'manage': None}
HOST_1_NAME = 'ocs-docker'
HOST_1_CFG = {'log-dir': '/simonsobs/log/ocs/',
              'crossbar': CROSSBAR_CFG,
              'agent-paths': ['/path/to/ocs/agents/'],
              'agent-instances': [INSTANCE_CFG]}
SITE_CFG = {'hub': HUB_CFG,
            'hosts': {HOST_1_NAME: HOST_1_CFG}}


def test_site_config_from_yaml(tmp_path):
    cfg_file = tmp_path / "default.yaml"
    with open(cfg_file, 'w') as f:
        yaml.dump(SITE_CFG, f)
    cfg = SiteConfig.from_yaml(cfg_file)
    assert cfg.data == SITE_CFG


def test_crossbar_config():
    cfg = CrossbarConfig(CROSSBAR_CFG)
    assert cfg.data == CROSSBAR_CFG


def test_hub_config():
    cfg = HubConfig(HUB_CFG)
    assert cfg.data == HUB_CFG


def test_host_config():
    cfg = HostConfig(HOST_1_CFG, name=HOST_1_NAME)
    assert cfg.data == HOST_1_CFG
    assert cfg.name == HOST_1_NAME
    assert cfg.crossbar == CrossbarConfig(CROSSBAR_CFG)


def test_instance_config():
    cfg = InstanceConfig(INSTANCE_CFG)
    assert cfg.data == INSTANCE_CFG


def test_arg_container_update():
    arg1 = ArgContainer(['--arg1', 'foo', '--arg2', 'bar'])
    arg2 = ArgContainer(['--arg2', 'baz'])
    arg1.update(arg2)
    assert arg1.to_list() == ['--arg1', 'foo', '--arg2', 'baz']


class TestGetControlClient:
    """Test site_config.get_control_client().

    """

    def test_wampy_client_type(self):
        """'wampy' client type should raise error."""
        mock_site = MagicMock()

        with pytest.raises(ValueError):
            get_control_client('test', site=mock_site, client_type='wampy')

    def test_unknown_client_type(self):
        """Unknown client type should raise error."""
        mock_site = MagicMock()

        with pytest.raises(ValueError):
            get_control_client('test', site=mock_site, client_type='unknown client')

    def test_none_client_type_w_wamp_http_site(self):
        """None client_type should determine type from site.hub.data."""
        mock_site = MagicMock()
        mock_site.hub.data = {'wamp_http': 'http://127.0.0.1:8001',
                              'wamp_realm': 'test_realm',
                              'address_root': 'observatory'}

        get_control_client('test', site=mock_site, client_type=None)

    def test_none_client_type_wo_wamp_http_site(self):
        """None client_type should determine type from site.hub.data. Missing
        'wamp_http' should fall back to the now unsupported 'wampy' client_type.

        """
        mock_site = MagicMock()
        mock_site.hub.data = {'wamp_realm': 'test_realm',
                              'address_root': 'observatory'}

        with pytest.raises(ValueError):
            get_control_client('test', site=mock_site, client_type=None)

    def test_missing_crossbar(self):
        crossbar_found = MagicMock(return_value="someplace/bin/crossbar")
        with patch("shutil.which", crossbar_found), \
                patch("os.path.exists", MagicMock(return_value=True)):
            config = CrossbarConfig({})
            assert config.binary == "someplace/bin/crossbar"

        # CrossbarConfig should only raise errors if someone tries to
        # use the invalid config.
        crossbar_not_found = MagicMock(return_value=None)
        with patch("shutil.which", crossbar_not_found):
            config = CrossbarConfig({})
        with pytest.raises(RuntimeError):
            config.get_cmd('start')

        config = CrossbarConfig({"bin": "not/a/valid/path/to/crossbar"})
        with pytest.raises(RuntimeError):
            config.get_cmd('start')
