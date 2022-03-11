import logging

from .digitalstrom import DsWebsocket
from .digitalstrom.device_collector import DssCollector

from .homekit import homekit
from dsHomekit import config

logging.basicConfig(
    level=getattr(logging, config.args.loglevel.upper()),
    format='%(asctime)s %(name)s.%(funcName)s : %(levelname)-8s [%(process)d] %(message)s',
)

homekit.setup()
dswebsocket = DsWebsocket()
