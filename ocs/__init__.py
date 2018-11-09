from .base import RET_VALS, OK, ERROR, TIMEOUT, get_ocs_config

from . import site_config

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
