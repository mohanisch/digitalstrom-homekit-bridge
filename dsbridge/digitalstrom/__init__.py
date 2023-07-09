from .eventpatcher import EventPatcher
from .const import SYSTEM_API

from ..config import read_config_file as config_file

if "token" in config_file():
    config_file = config_file()
    from dsbridge.digitalstrom.device_collector import DssCollector
    from dsbridge.digitalstrom.device_collector import DssStateCollector

    device_collector = DssCollector()
    state_collector = DssStateCollector()
    event_patcher = EventPatcher()
