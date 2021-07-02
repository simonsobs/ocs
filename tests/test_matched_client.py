import os
from unittest.mock import MagicMock, patch
from ocs.matched_client import MatchedClient

mocked_client = MagicMock()
mock_from_yaml = MagicMock()


@patch('ocs.client_http.ControlClient', mocked_client)
@patch('ocs.site_config.SiteConfig.from_yaml', mock_from_yaml)
@patch('sys.argv', ['example_client.py', 'test'])
def test_extra_argv():
    """If there are extra arguments in sys.argv and args=[] is not set when
    instantiating a MatchedClient, then internally
    site_config.get_control_client() will inspect sys.argv[1:], which causes
    issues down the line when run through the site_config parser.

    Here we patch in a mocked ControlClient to avoid needing to talk to a
    crossbar server. We also patch in a mocked from_yaml() method, to avoid
    needing to read a real site file. Lastly, and most importantly, we patch in
    sys.argv with an actual additional argument. This will cause an
    "unrecognized arguments" error when argparse inspects sys.argv within the
    site_config parser.

    """
    # Set for get_config to pick up on
    os.environ["OCS_CONFIG_DIR"] = '/tmp/'
    MatchedClient("test")
