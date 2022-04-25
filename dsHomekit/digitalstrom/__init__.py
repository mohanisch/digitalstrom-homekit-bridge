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

    def device_event(
            self, dsuid: str,
            zoneid: int,
            attributes: dict,
            application: str = ""
    ):
        _count_hap_events = len(self.hap_events)
        _count_device_events = 0

        if dsuid in self.hap_events and _count_device_events <= _count_hap_events:
            self.device_events[dsuid] = {
                "zoneid": zoneid,
                "attributes": attributes
            }
            _count_device_events = len(self.device_events)

        if _count_device_events == _count_hap_events:
            _state = None
            _actionid = None

            zone_devices = collector.get_zone(zoneid)['devices']
            result = all(elem in list(self.device_events.keys()) for elem in zone_devices[application])

            def zone_state(attribute):
                self.varname = attribute
                _v = []
                for e, a in self.device_events.items():
                    _v.append(a['attributes'][self.varname])
                _v.sort()
                return True if _v[0] == 100 and all(x in (0, 100) for x in _v) else False

            if application == 'lights':
                _state = zone_state('brightness')
                _actionid = "on" if _state else "off"
            if application == 'shades':
                _state = zone_state('shadePositionOutside')
                _actionid = "up" if _state else "down"

            if result:
                patch_zone(zoneid, application, _actionid)
            else:
                for dsuid, values in self.device_events.items():
                    patch_device(
                        dsuid, values['attributes'], _actionid
                    )
            self.clean_events()

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
    dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)


@threaded
def patch_device(dsuid: str, attributes: dict, actionid: str):
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

        device_scenario = {
            "context": "applicationDevice",
            "actionId": actionid,
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


def patch_switch(switch_id: str, state: bool):
    switch_attributes = []
    if switch_id in ('apartmentAbsents', 'dummy'):
        switch_scenario = {
            "context": "applicationApartment",
            "actionId": "absent" if state else "present",
            "application": "access"
        }
        payload = json.dumps(switch_scenario).encode("UTF-8")
        dsrequest.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
    else:
        switch_attribute = {
            "op": "replace",
            "path": "/status",
            "value": "active" if state else "inactive"
        }
        switch_attributes.append(switch_attribute)
        payload = json.dumps(switch_attributes).encode("UTF-8")
        dsrequest.patch(SMART_HOME_API + '/userDefinedStates/' + switch_id + '/status', data=payload)
