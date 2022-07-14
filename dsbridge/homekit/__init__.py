from __future__ import annotations

import _thread
import logging
from collections.abc import Callable

from .const import CONTROL, STATE_ON, STATE_OFF, STATE_UP, STATE_DOWN
from .. import config

from .accessories import get_accessory, DsAccessoryDriver, DsBridge
from .aid_manager import AccessoryAidStorage
from .util import async_show_setup_message

from ..digitalstrom.device_collector import DssCollector
from ..digitalstrom import EventPatcher

collector = DssCollector()

STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_STOPPED = 2
STATUS_WAIT = 3

CALLBACK_TYPE = Callable[[], None]


def add_devices():
    file = config.read_config_file()['entities']
    for dsdevice in file:   # dsdevices:
        homekit.add_bridge_accessory(dsdevice)


def start_homekit():
    def run_homekit():
        homekit.setup()
        collector.gather_devices_status()
        add_devices()
        logging.info("Start homekit...")
        homekit.start()

    _thread.start_new_thread(run_homekit, ())


class EventDecider(object):
    def __init__(self):
        self.hap_events = None
        self.device_events = {}

        self.ep = EventPatcher()

    def recieve_hap_event(self, events):
        _events = {}
        for event in events:
            if 'ev' in event:
                continue
            else:
                entity_id = get_entity_by_aid(event['aid'])
                _events[entity_id] = {}
                self.hap_events = list(dict.fromkeys(_events))

    def device_event(
            self,
            entity_id: str,
            dsuid: str,
            zoneid: int,
            attributes: dict,
            application: str = ""
    ):
        _count_hap_events = len(self.hap_events)
        _count_device_events = 0
        _test_action = None

        if entity_id in self.hap_events and _count_device_events <= _count_hap_events:
            self.device_events[entity_id] = {
                "dsuid": dsuid,
                "zoneid": zoneid,
                "attributes": attributes,
                "application": application,
                "action": _test_action
            }
            _count_device_events = len(self.device_events)

        if _count_device_events == _count_hap_events:
            _zone_ids, _applications = [], []
            _event_type, _zoneid = "", ""

            zone_devices = config.read_config_file()['zones']
            zones = ({v['id']: v for v in zone_devices})

            for k, v in self.device_events.items():
                _zone_ids.append(v["zoneid"])
            for k, v in self.device_events.items():
                _applications.append(v["application"])

            for zoneid in list(set(_zone_ids)):
                for app in list(set(_applications)):
                    _v = []
                    _application = app

                    if _application in CONTROL and "scene" in CONTROL[_application]:
                        _event_type, _zoneid = ("zone", zoneid) if all(
                            elem in list(self.device_events.keys()) for elem in zones[zoneid]['applications'][_application]) else ("device", zoneid)
                    else:
                        _event_type = "manualState"

                    if _event_type == "zone":
                        for e, a in self.device_events.items():
                            _value = a['attributes'][CONTROL[_application]['id']]
                            if a['zoneid'] == _zoneid:
                                if _application and a['application'] == _application:
                                    _v.append(_value)
                                    _v.sort()
                        _zone_scene = True if _v[0] in (0, 100) else False
                        if not _zone_scene:
                            _event_type = "device"
                        else:
                            action = CONTROL[_application]['scene'][_v[0]]
                            self.ep.patch_zone(zoneid, _application, action)

                    if _event_type == "device":
                        for e, a in self.device_events.items():
                            if a['zoneid'] == _zoneid:
                                if _application and a['application'] == _application:
                                    if a['attributes'][CONTROL[_application]['id']] in (0, 100):
                                        _value = a['attributes'][CONTROL[_application]['id']]
                                        action = CONTROL[_application]['scene'][_value]
                                        self.ep.patch_device_scenario(
                                            a['dsuid'], action
                                        )
                                    else:
                                        self.ep.patch_device_status(
                                            a['dsuid'], a['attributes']
                                        )

                    if _event_type == "manualState":
                        for e, a in self.device_events.items():
                            print(e, a)
                            if _application and a['application'] == _application:
                                self.ep.patch_switch(
                                    a['dsuid'], a['attributes']
                                )


            self.clean_events()

    def _action(self, action):
        return all(value['action'] == action for value in self.device_events.values())

    def clean_events(self):
        self.hap_events = None
        self.device_events = {}


event_decider = EventDecider()


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
        self.driver = DsAccessoryDriver(
            port=self._port,
            persist_file=self.persist_file
        )
        self.bridge = DsBridge(self.driver, self._name)
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

    def start(self):
        self.driver.start()

    def stop(self):
        self.driver.stop()

    def signal_handler(self, _signal, _frame):
        self.driver.signal_handler(_signal, _frame)

    def set_allocations(self):
        return self.aid_storage.allocations

    def bridge_state(self):
        return self.bridge.driver.state


def get_aid_by_dsuid(dsuid: str):
    """Returns aid by given dsuid"""
    aid = None
    if dsuid in homekit.aid_storage.allocations.keys():
        aid = homekit.aid_storage.allocations[dsuid]
    return aid


def get_entity_by_aid(aid: int):
    """Returns dsuid by given aid"""
    entity_id = None
    allocations = homekit.aid_storage.allocations

    if aid in allocations.values():
        entity_id = list(allocations.keys())[list(allocations.values()).index(aid)]
    return entity_id


homekit = HomeKit(
    name=config.args.homekit_bridge_name,
    port=51826,
    persist_file=(config.args.persit_file_path + "/" + config.args.persit_file_name)
)
