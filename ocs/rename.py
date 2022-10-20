import os
import datetime


def _find_all_g3_files(target):
    """Build list of .g3 files.

    Parameters
    ----------
    target : str
        File or directory to scan.

    Returns
    -------
    list
        List of full paths to .g3 files.

    """
    _file_list = []
    if os.path.isfile(target):
        _file_list.append(target)
    elif os.path.isdir(target):
        a = os.walk(target)
        for root, _, _file in a:
            for g3 in _file:
                if g3[-2:] == "g3":
                    _file_list.append(os.path.join(root, g3))

    return _file_list


def _remove_non_matching_files(filelist, verbose=None):
    """Make new list, removing files that don't match the known stringtime format.

    If the script was partially run on a directory, newly renamed files will
    cause errors at the strptime step, so remove them.

    Parameters
    ----------
    filelist : list
        List of files, probably made by _find_all_g3_files()
    verbose : int
        Verbosity level.

    Returns
    -------
    list
        List of full paths to .g3 files.

    """
    new_list = []
    for f in filelist:
        try:
            basename = os.path.basename(f)
            datetime.datetime.strptime(basename, "%Y-%m-%d-%H-%M-%S.g3")
            new_list.append(f)
        except ValueError:
            if verbose is not None:
                print(f"{f} does not match datestring format, removing from list.")

    return new_list


def build_filelist(target, verbose=None):
    """Build .g3 filelist to process.

    This is done in two steps, finding all *.g3 files, then making sure they
    match the old naming convention.

    Parameters
    ----------
    target : str
        File or directory to scan.
    verbose : int
        Verbosity level.

    Returns
    -------
    list
        List of full paths to .g3 files.

    """

    _filelist = _find_all_g3_files(target)
    filelist = _remove_non_matching_files(_filelist, verbose)

    return filelist


def _generate_ctime_filename(path):
    """Determine the ctime corresponding to a datestring formatted filename.

    Note: Files must be named with a UTC timestamp for this to work properly.
    However, the code works on any timezone machine. If files are not named based
    on UTC timestamps, then this will result in a shifted timestamp after
    conversion.

    Paramters
    ---------
    path : str
        Full path to old datestring style .g3 file.

    Returns
    -------
    str
        File basename in new ctime based format.

    """
    basename = os.path.basename(path)
    dt = datetime.datetime.strptime(basename, "%Y-%m-%d-%H-%M-%S.g3")
    ctime = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
    new_filename = f"{ctime}.g3"

    return new_filename


def _rename_file(path, verbose=None):
    """Rename a single file from "%Y-%m-%d-%H-%M-%S.g3" to "ctime.g3".

    Paramters
    ---------
    path : str
        Filename for .g3 file.
    verbose : int
        Verbosity level.

    """
    dirname = os.path.dirname(path)
    new_filename = _generate_ctime_filename(path)
    new_path = os.path.join(dirname, new_filename)
    if verbose is not None:
        print(f"Renaming {path} to {new_path}")

    # Don't overwrite any existing file.
    if os.path.isfile(new_path):
        raise OSError("File at dst, {new_path}, already exists!")

    os.rename(path, new_path)


def rename_files(path, verbose=None):
    """Rename all .g3 file in path to new ctime based format.

    Paramters
    ---------
    path : str
        Filename for .g3 file.
    verbose : int
        Verbosity level.

    """
    filelist = build_filelist(path, verbose)

    for f in filelist:
        _rename_file(f, verbose)


def main(target, verbose=None):
    rename_files(target, verbose)
