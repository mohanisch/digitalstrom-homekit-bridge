"""
Homekit module which handles homekit relate stuff
"""
from __future__ import annotations

import logging
import threading

from dsbridge import config
from dsbridge.const import STATUS_READY
from dsbridge.digitalstrom import state_collector
from dsbridge.homekit.accessories import DsAccessoryDriver, DsBridge, get_accessory
from dsbridge.homekit.aid_manager import AccessoryAidStorage
from dsbridge.homekit.event_handler import EventDecider

logger = logging.getLogger(__name__)

# Thread reference for homekit
_homekit_thread = None


def start_homekit():
    """Start homekit in a separate thread."""
    global _homekit_thread

    def add_devices():
        try:
            file = config.read_config_file()
            if 'entities' not in file:
                logger.warning("No entities found in config")
                return

            # Check device availability before adding to HomeKit
            available_states = state_collector.gather_devices_status()

            for dsdevice in file['entities']:
                # Skip devices that are not available in digitalSTROM
                entity_id = dsdevice.get('entity_id')
                if entity_id not in available_states:
                    logger.warning(
                        "Skipping unavailable device %s (%s) - not found in digitalSTROM",
                        dsdevice.get('name', 'unknown'),
                        entity_id
                    )
                    continue

                try:
                    homekit.add_bridge_accessory(dsdevice)
                except Exception as e:
                    logger.error(
                        "Failed to add accessory %s: %s",
                        dsdevice.get('name', 'unknown'),
                        e,
                        exc_info=True
                    )
        except Exception as e:
            logger.error("Error adding devices: %s", e, exc_info=True)

    def run_homekit():
        try:
            homekit.setup()
            state_collector.gather_devices_status()
            add_devices()
            logger.info("Starting homekit...")
            homekit.start()
        except Exception as e:
            logger.error("Fatal error in homekit thread: %s", e, exc_info=True)

    if _homekit_thread is None or not _homekit_thread.is_alive():
        _homekit_thread = threading.Thread(
            target=run_homekit,
            daemon=True,
            name="homekit-runner"
        )
        _homekit_thread.start()
    else:
        logger.warning("Homekit thread is already running")


def stop_homekit():
    """
    Stop homekit implementation
    """
    logging.info("Stopping homekit...")
    homekit.stop()


class HomeKit:
    """
    Homekit class
    """

    def __init__(
            self,
            name,
            port,
            persist_file,
            address=None,
            pincode=None,
            devices=None,
    ):
        """Initialize a HomeKit object."""
        self._name = name
        self._port = port
        self._address = address
        self._pincode = pincode
        self._devices = devices or []

        self.persist_file = persist_file
        self.aid_storage = AccessoryAidStorage()
        self.status = STATUS_READY

        self.bridge = None
        self.driver = None

    def setup(self):
        """Set up bridge and accessory driver."""
        logging.info("Setup HomeKit driver")
        self.driver = DsAccessoryDriver(
            port=self._port,
            address=self._address,
            persist_file=self.persist_file
        )
        self.bridge = DsBridge(self.driver, self._name)
        self.driver.add_accessory(accessory=self.bridge)

    def add_bridge_accessory(self, device):
        aid = self.aid_storage.get_or_allocate_aid(device['entity_id'])

        try:
            acc = get_accessory(self.driver, device, aid)
            if acc is not None:
                self.bridge.add_accessory(acc)
                return acc
        except Exception:
            logging.exception("Failed to create a HomeKit accessory for %s (%s)", device['name'], device['dsuid'])
        return None

    def start(self):
        self.driver.start()

    def stop(self):
        return self.driver.stop()

    def signal_handler(self, _signal, _frame):
        self.driver.signal_handler(_signal, _frame)

    def set_allocations(self):
        return self.aid_storage.allocations

    def bridge_state(self):
        return self.bridge.driver.state


homekit = HomeKit(
    name=config.args.homekit_bridge_name,
    address=config.args.homekit_address,
    port=config.args.homekit_port,
    persist_file=(config.args.persit_file_path + "/" + config.args.persit_file_name)
)
event_decider = EventDecider()
