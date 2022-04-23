import json

from .const import SMART_HOME_API
from ..config import args
from .device_collector import DssCollector
from .request_handler import DsRequest
from ..utils.helper import threaded

dsrequest = DsRequest("https://" + args.hostname + ":" + args.http_port + "/")
collector = DssCollector()


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

    def recieve_device_event(self, dsuid: str, zoneid: int, attributes: dict, application: str = ""):
        _count_hap_events = len(self.hap_events)
        _count_device_events = 0

        if dsuid in self.hap_events and _count_device_events <= _count_hap_events:
            self.device_events[dsuid] = {
                "zoneid": zoneid,
                "attributes": attributes
            }
            _count_device_events = len(self.device_events)

        if _count_device_events == _count_hap_events:
            zone_devices = collector.get_zone(zoneid)['devices']
            result = all(elem in list(self.device_events.keys()) for elem in zone_devices[application])
            if result:
                _state = None

                def zone_state(attribute):
                    self.varname = attribute
                    _v = []
                    for e, a in self.device_events.items():
                        _v.append(a['attributes'][self.varname])
                    _v.sort()
                    return True if _v[0] == 100 and all(x in (0, 100) for x in _v) else False

                if application == 'lights':
                    _state = zone_state('brightness')
                if application == 'shades':
                    _state = zone_state('shadePositionOutside')

                patch_zone(zoneid, _state, application)
            else:
                for dsuid, values in self.device_events.items():
                    patch_device(
                        dsuid, values['attributes']
                    )
            event_decider.clean_events()

    def get_events(self):
        return self.hap_events

    def clean_events(self):
        self.hap_events = []
        self.device_events = {}


event_decider = EventDecider()


@threaded
def patch_zone(zoneid: int, state: bool, application: str):
    zone_scenario = {
        "context": "applicationZone",
        "actionId": "on" if state else "off",
        "application": application,
        "zone": zoneid
    }
    payload = json.dumps(zone_scenario).encode("UTF-8")
    dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)


@threaded
def patch_device(dsuid: str, attributes: dict):
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
        actionId = ""
        if 'brightness' in attributes:
            actionId = "on" if attributes['brightness'] == 100 else "off"
        if 'shadePositionOutside' in attributes:
            actionId = "on" if attributes['shadePositionOutside'] == 100 else "off"

        device_scenario = {
            "context": "applicationDevice",
            "actionId": actionId,
            "application": "",
            "area": "",
            "zone": "",
            "dsDevice": dsuid
        }
        payload = json.dumps(device_scenario).encode("UTF-8")
        dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
    else:
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
        dsrequest.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)


def patch_switch(user_defined_state_id: str, state: bool):
    print(user_defined_state_id, state)
    switch_attributes = {
        "op": "replace",
        "path": "/status",
        "value": "active" if state else "inactive"
    }
    payload_raw = [switch_attributes]
    payload = json.dumps(payload_raw).encode("UTF-8")
    dsrequest.patch('userDefinedStates/' + user_defined_state_id + '/status', payload=payload)
