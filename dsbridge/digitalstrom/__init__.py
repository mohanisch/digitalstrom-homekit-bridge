# Import classes
from dsbridge.digitalstrom.device_collector import DssCollector
from dsbridge.digitalstrom.device_collector import DssStateCollector
from .const import SYSTEM_API
from .eventpatcher import EventPatcher
from ..config import read_config_file as config_file

# Initialize collectors - they will be properly initialized when token is available
# This allows imports to work even before configuration is complete
try:
    config = config_file()
    if config.get("token"):
        device_collector = DssCollector()
        state_collector = DssStateCollector()
        try:
            event_patcher = EventPatcher()
        except Exception:
            # EventPatcher requires token, so set to None if it fails
            event_patcher = None
    else:
        # Create instances but they won't work until token is configured
        device_collector = DssCollector()
        state_collector = DssStateCollector()
        event_patcher = None  # EventPatcher requires token, so set to None
except Exception:
    # If config file doesn't exist or can't be read, create empty instances
    # They will be reinitialized when config is available
    device_collector = DssCollector()
    state_collector = DssStateCollector()
    event_patcher = None
