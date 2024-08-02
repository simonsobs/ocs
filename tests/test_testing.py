# import os
# import time
# import pytest
#
# from unittest.mock import patch

from ocs.testing import AgentRunner


def test_agent_runner(tmpdir):
    runner = AgentRunner('../ocs/agents/fake_data/agent.py', 'fake_data', args=None)
    runner.run(timeout=10)
    runner.shutdown()


# def test_make_filename_directory_creation_no_subdirs(tmpdir):
#    """make_filename() should raise a FileNotFoundError if make_subdirs is
#    False.
#
#    """
#    test_dir = os.path.join(tmpdir, 'data')
#    with pytest.raises(FileNotFoundError):
#        make_filename(test_dir, make_subdirs=False)
#
#
# def test_make_filename_directory_creation_permissions(tmpdir):
#    """make_filename() should raise a PermissionError if it runs into one when
#    making the directories.
#
#    Here we mock raising the PermissionError on the makedirs call.
#
#    """
#    test_dir = os.path.join(tmpdir, 'data')
#    with patch('os.makedirs', side_effect=PermissionError('mocked permission error')):
#        with pytest.raises(PermissionError) as e_info:
#            make_filename(test_dir)
#        assert str(e_info.value) == 'mocked permission error'
