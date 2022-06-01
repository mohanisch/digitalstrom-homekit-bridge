import json
import logging

from .const import SMART_HOME_API
from ..config import args
from .device_collector import DssCollector
from .request_handler import DsRequest
from ..utils.helper import threaded

dsrequest = DsRequest("https://" + args.hostname + ":" + args.http_port + "/")
collector = DssCollector()

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
                from ..homekit import get_dsuid_by_aid
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
                    patch_device(
                        dsuid, value['attributes']
                    )
            else:
                for dsuid, value in self.device_events.items():
                    _state, _actionid = self._zone_state(value, value['application'])

                    if _state == "zone":
                        patch_zone(zoneid, value['application'], _actionid)
                    if _state == "device":
                        patch_device(
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


@threaded
def patch_zone(zoneid: int, application: str, actionid: str):
    zone_scenario = {
        "context": "applicationZone",
        "actionId": actionid,
        "application": application,
        "zone": zoneid
    }
    payload = json.dumps(zone_scenario).encode("UTF-8")
    logging.debug("(patch_zone) Payload: %s", payload)
    dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)


@threaded
def patch_device(dsuid: str, attributes: dict, actionid: str = ""):
    def patch_device_scenario():
        device_scenario = {
            "context": "applicationDevice",
            "actionId": actionid,
            "dsDevice": dsuid
        }
        payload = json.dumps(device_scenario).encode("UTF-8")
        logging.debug("(patch_device_scenarios) Payload: %s", payload)
        dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)

    def patch_device_status():
        device_attributes = []
        for output_id, value in attributes.items():
            _set_attributes = True
            device_attribute = {
                "op": "replace",
                "path": "/functionBlocks/" + dsuid + "/outputs/" + output_id + "/value",
                "value": str(value)
            }
            device_attributes.append(device_attribute)

        payload = json.dumps(device_attributes).encode("UTF-8")
        logging.debug("(patch_device) Payload: %s", payload)
        dsrequest.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)

    if (
            (
                    'brightness' in attributes and attributes['brightness'] in (100, 0)
                    and 'colortemp' not in attributes
                    and 'saturation' not in attributes
            ) or
            (
                    'shadePositionOutside' in attributes
                    and attributes['shadePositionOutside'] in (100, 0)
            )
    ):
        patch_device_scenario()
    else:
        patch_device_status()


def patch_switch(switch_id: str, state: bool):
    switch_attributes = []
    if switch_id in ('apartmentAbsents', 'dummy'):
        switch_scenario = {
            "context": "applicationApartment",
            "actionId": "absent" if state else "present",
            "application": "access"
        }
        payload = json.dumps(switch_scenario).encode("UTF-8")
        logging.debug("(patch_switch) Payload: %s", payload)
        dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
    else:
        switch_attribute = {
            "op": "replace",
            "path": "/status",
            "value": "active" if state else "inactive"
        }
        switch_attributes.append(switch_attribute)
        payload = json.dumps(switch_attributes).encode("UTF-8")
        logging.debug("Payload: %s", payload)
        dsrequest.patch(SMART_HOME_API + '/userDefinedStates/' + switch_id + '/status', data=payload)
