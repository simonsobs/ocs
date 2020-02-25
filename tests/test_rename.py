import pytest
import os
from pathlib import Path

from ocs import rename

def test_rename_files(tmpdir):
    p = tmpdir.mkdir("data")
    Path(os.path.join(p, "2020-01-01-12-00-00.g3")).touch()

    rename.rename_files(p)

    assert os.path.isfile(os.path.join(p, "1577880000.g3"))
