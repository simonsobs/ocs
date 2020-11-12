import ocs
from enum import Enum

RET_VALS = {
    'OK': 0,
    'ERROR': -1,
    'TIMEOUT': 1,
}

OK = RET_VALS['OK']
ERROR = RET_VALS['ERROR']
TIMEOUT = RET_VALS['TIMEOUT']

class OpCode(Enum):
    """
    Enumeration of OpSession states.
    """
    NONE = 1
    STARTING = 2
    RUNNING = 3
    STOPPING = 4
    SUCCEEDED = 5
    FAILED = 6
    EXPIRED = 7
