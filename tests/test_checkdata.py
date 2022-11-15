try:
    # dependent on so3g
    from ocs.checkdata import DataChecker  # noqa: F401
except ModuleNotFoundError as e:
    print(f"Unable to import: {e}")
