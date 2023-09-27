"""
Homekit module which handles homekit relate stuff
"""
from __future__ import annotations

import _thread
import logging

from dsbridge import config
from dsbridge.const import STATUS_READY
from dsbridge.homekit.accessories import DsAccessoryDriver, DsBridge, get_accessory
from dsbridge.homekit.aid_manager import AccessoryAidStorage
from dsbridge.homekit.event_handler import EventDecider
from dsbridge.digitalstrom import state_collector


def start_homekit():
    def add_devices():
        file = config.read_config_file()
        for dsdevice in file['entities']:
            homekit.add_bridge_accessory(dsdevice)

    def run_homekit():
        homekit.setup()
        state_collector.gather_devices_status()
        add_devices()
        logging.info("Start homekit...")
        homekit.start()

    _thread.start_new_thread(run_homekit, ())


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
