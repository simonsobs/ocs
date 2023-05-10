from unittest.mock import MagicMock, patch

import pytest
from ocs.site_config import get_control_client, CrossbarConfig


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
            config = CrossbarConfig.from_dict({})
            assert config.binary == "someplace/bin/crossbar"

        # CrossbarConfig should only raise errors if someone tries to
        # use the invalid config.
        crossbar_not_found = MagicMock(return_value=None)
        with patch("shutil.which", crossbar_not_found):
            config = CrossbarConfig.from_dict({})
        with pytest.raises(RuntimeError):
            config.get_cmd('start')

        config = CrossbarConfig.from_dict({"bin": "not/a/valid/path/to/crossbar"})
        with pytest.raises(RuntimeError):
            config.get_cmd('start')
