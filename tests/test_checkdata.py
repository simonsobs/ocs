try:
    # dependent on so3g
    from ocs.checkdata import DataChecker
except ModuleNotFoundError as e:
    print(f"Unable to import: {e}")
