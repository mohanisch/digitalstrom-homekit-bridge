from __future__ import annotations

import _thread
import logging
from collections.abc import Callable
from dsHomekit import config

from .accessories import get_accessory, DsAccessoryDriver, DsBridge
from .aid_manager import AccessoryAidStorage
from .util import async_show_setup_message

from dsHomekit.digitalstrom.device_collector import DssCollector
from dsHomekit.digitalstrom import EventPatcher

collector = DssCollector()

STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_STOPPED = 2
STATUS_WAIT = 3

CALLBACK_TYPE = Callable[[], None]


def add_devices():
    dsdevices = collector.get_entities()

    for dsdevice in dsdevices:
        homekit.add_bridge_accessory(dsdevice)


def start_homekit():
    def run_homekit():
        homekit.setup()
        add_devices()
        logging.info("Start homekit...")
        homekit.start()

    _thread.start_new_thread(run_homekit, ())


STATE_ON = "on"
STATE_OFF = "off"
STATE_UP = "up"
STATE_DOWN = "down"


class EventDecider(object):
    def __init__(self):
        self.hap_events = None
        self.device_events = {}

    def recieve_hap_event(self, events):
        _events = {}
        for event in events:
            if 'ev' in event:
                continue
            else:
                dsuid = get_dsuid_by_aid(event['aid']).split('.')[0]
                _events[dsuid] = {}
                self.hap_events = list(dict.fromkeys(_events))

    def device_event(
            self, dsuid: str,
            zoneid: int,
            attributes: dict,
            application: str = ""
    ):
        _count_hap_events = len(self.hap_events)
        _count_device_events = 0

        if "brightness" in attributes:
            _test_action = STATE_OFF if attributes['brightness'] == 0 else STATE_ON if attributes[
                                                                                           'brightness'] == 100 else "dimm"
        else:
            _test_action = "bla"

        if dsuid in self.hap_events and _count_device_events <= _count_hap_events:
            self.device_events[dsuid] = {
                "zoneid": zoneid,
                "attributes": attributes,
                "application": application,
                "action": _test_action
            }
            _count_device_events = len(self.device_events)

        if _count_device_events == _count_hap_events:

            # if self._action('on'):
            #     print("on", self._action('on'))
            # if self._action('off'):
            #     print("off", self._action('off'))
            if self._action('dimm'):
                for dsuid, value in self.device_events.items():
                    EventPatcher().patch_device(
                        dsuid, value['attributes']
                    )
            else:
                for dsuid, value in self.device_events.items():
                    _state, _actionid = self._zone_state(value, value['application'])

                    if _state == "zone":
                        EventPatcher().patch_zone(zoneid, value['application'], _actionid)
                    if _state == "device":
                        EventPatcher().patch_device(
                            dsuid, value['attributes'], _actionid
                        )

            self.clean_events()

    def _action(self, action):
        return all(value['action'] == action for value in self.device_events.values())

    def _zone_state(self, value, _application):  # TODO: func name muss angepasst werden
        zone_devices = collector.get_zone(value['zoneid'])['devices']
        _v = []
        STATE_TRUE, STATE_FALSE = "", ""

        _event_type = "zone" if all(
            elem in list(self.device_events.keys()) for elem in zone_devices[_application]) else "device"

        # TODO: Muss als constante hinterlegt werden, für jeden möglichen type
        if value['application'] == 'lights':
            self.varname = "brightness"
            STATE_TRUE = STATE_ON
            STATE_FALSE = STATE_OFF
        if value['application'] == 'shades':
            self.varname = "shadePositionOutside"
            if _event_type == "device":
                STATE_TRUE = STATE_ON
                STATE_FALSE = STATE_OFF
            else:
                STATE_TRUE = STATE_UP
                STATE_FALSE = STATE_DOWN

        for e, a in self.device_events.items():
            if a['application'] == _application:
                _v.append(a['attributes'][self.varname])
        _v.sort()

        return \
            _event_type, \
            STATE_TRUE if _v[0] == 100 else STATE_FALSE

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


def get_dsuid_by_aid(aid: int):
    """Returns dsuid by given aid"""
    dsuid = None
    allocations = homekit.aid_storage.allocations

    if aid in allocations.values():
        dsuid = list(allocations.keys())[list(allocations.values()).index(aid)]
    return dsuid


homekit = HomeKit(
    name=config.args.homekit_bridge_name,
    port=51826,
    persist_file=(config.args.persit_file_path + "/" + config.args.persit_file_name)
)
