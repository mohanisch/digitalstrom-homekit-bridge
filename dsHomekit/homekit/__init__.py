from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.util import callback

from dsHomekit import config
from .accessories import get_accessory
from .aid_manager import AccessoryAidStorage
from . import type_lights, type_windowcover, type_sensors, type_switch
from .util import async_show_setup_message
from ..core import Event

STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_STOPPED = 2
STATUS_WAIT = 3

CALLBACK_TYPE = Callable[[], None]


class HomeKit:
    def __init__(
            self,
            name,
            port,
            persist_file,
            pincode=None,
            devices=None,
    ):
        """Initialize a HomeKit object."""
        self._name = name
        self._port = port
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
        self.driver = AccessoryDriver(
            port=self._port,
            persist_file=self.persist_file
        )
        self.bridge = Bridge(self.driver, self._name)
        self.driver.add_accessory(accessory=self.bridge)

    def add_bridge_accessory(self, device):
        """Set up bridge and accessory."""
        aid = self.aid_storage.get_or_allocate_aid(unique_id=device['entity_id'])

        try:
            acc = get_accessory(self.driver, device, aid)
            if acc is not None:
                self.bridge.add_accessory(acc)
                return acc
        except Exception:
            logging.exception("Failed to create a HomeKit accessory for %s (%s)", device['name'], device['dsuid'])
        return None

    @callback
    def _async_show_setup_message(self):
        """Show the pairing setup message."""
        async_show_setup_message(
            "self.entry_id",
            "self._entry_title", self.driver.accessory,
            self.driver.state.pincode,
            self.driver.accessory.xhm_uri(),
        )

    def start(self):
        self.driver.start()

    def stop(self):
        self.driver.stop()

    def signal_handler(self, _signal, _frame):
        self.driver.signal_handler(_signal, _frame)

    def set_allocations(self):
        return self.aid_storage.allocations


def get_aid_by_dsuid(dsuid: str):
    """Returns aid by given dsuid"""
    aid = None
    if dsuid in homekit.aid_storage.allocations.keys():
        aid = homekit.aid_storage.allocations[dsuid]
    return aid


def get_dsuid_by_aid(aid: int):
    """Returns dsuid by given aid"""
    dsuid = None
    allocations = homekit.aid_storage.allocations
    if aid in allocations.values():
        dsuid = list(allocations.keys())[list(allocations.values()).index(aid)]
    return dsuid


def async_track_state_change_event(
        entity_ids: str | Iterable[str],
        action: Callable[[Event], Any],
) -> CALLBACK_TYPE:
    for entity_id in entity_ids:
        print(entity_id, action)

    return entity_id


homekit = HomeKit(
    name=config.args.homekit_bridge_name,
    port=51826,
    persist_file=(config.args.persit_file_path + "/" + config.args.persit_file_name)
)
