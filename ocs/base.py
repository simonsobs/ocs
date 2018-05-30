import ocs

RET_VALS = {
    'OK': 0,
    'ERROR': -1,
    'TIMEOUT': 1,
}

OK = RET_VALS['OK']
ERROR = RET_VALS['ERROR']
TIMEOUT = RET_VALS['TIMEOUT']


def get_ocs_config():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read('ocs.cfg')
    return config
