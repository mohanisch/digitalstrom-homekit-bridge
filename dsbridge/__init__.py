import logging
from .config import read_config_file as c
from .helper import remove_control_characters, threaded


def _loglevel():
    config_file = c()
    loglevel = config.args.loglevel.upper()
    if config_file is not None and 'loglevel' in config_file:
        loglevel = config_file['loglevel'].upper()

    return loglevel


logging.basicConfig(
    level=getattr(logging, _loglevel()),
    format='%(asctime)s %(name)s.%(funcName)s : %(levelname)-8s [%(process)d] %(message)s',
)
