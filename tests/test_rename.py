import pytest
import os
from pathlib import Path

from ocs import rename

def test_rename_main(tmpdir):
    """Test rename.main(), should hit most of the rename module. Tests renaming
    a directory with a single file in it.

    """
    p = tmpdir.mkdir("data")
    Path(os.path.join(p, "2020-01-01-12-00-00.g3")).touch()

    rename.main(p, verbose=1)

    assert os.path.isfile(os.path.join(p, "1577880000.g3"))

def test_rename_single_file(tmpdir):
    """target can be a single file, so we test tarting a file instead of a
    directory.

    """
    p = tmpdir.mkdir("data")
    filename = "2020-01-01-12-00-00.g3"
    Path(os.path.join(p, filename)).touch()

    rename.main(os.path.join(p, filename))

    assert os.path.isfile(os.path.join(p, "1577880000.g3"))

def test_nonmatching_filename(tmpdir):
    """Files must match the datestring time format, else we won't run them.
    Test that we skip these files.

    """
    p = tmpdir.mkdir("data")
    filename = "2020-01-01-12-00-00_non_match.g3"
    Path(os.path.join(p, filename)).touch()

    rename.main(os.path.join(p, filename))
    rename.main(os.path.join(p, filename), verbose=1)

    # file should remain unaffected
    assert os.path.isfile(os.path.join(p, filename))

def test_file_collision(tmpdir):
    """If we somehow end up with a matching timestring we shouldn't overwrite
    the existing file. This checks an error is raised in this case.

    """
    p = tmpdir.mkdir("data")
    filename = "2020-01-01-12-00-00.g3"
    Path(os.path.join(p, filename)).touch()
    # Make our own renamed file to collide
    Path(os.path.join(p, "1577880000.g3")).touch()

    with pytest.raises(OSError):
        rename.main(os.path.join(p, filename))
