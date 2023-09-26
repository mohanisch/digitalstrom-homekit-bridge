"""
Event hanlder
"""
from .const import CONTROL
from .. import config
from ..digitalstrom import event_patcher


def get_entity_by_aid(aid: int):
    """Returns dsuid by given aid"""
    from . import homekit
    entity_id = None
    allocations = homekit.aid_storage.allocations

    if aid in allocations.values():
        entity_id = list(allocations.keys())[list(allocations.values()).index(aid)]
    return entity_id


class EventDecider:
    """
    EventDecider is checking if the request can be
    applied as a zone or as a device only scene. It is based
    on the switched devices if they are in the same zone (dS) or not.
    """

    def __init__(self):
        self.hap_events = None
        self.device_events = {}

        self.event_patcher = event_patcher

    def receive_hap_event(self, events):
        """
        Getting events from HAP
        """
        _events = {}
        for event in events:
            if 'ev' in event:
                continue

            entity_id = get_entity_by_aid(event['aid'])
            _events[entity_id] = {}
            self.hap_events = list(dict.fromkeys(_events))

    def device_event(self, entity_id: str, dsuid: str, zoneid: int, attributes: dict, application: str = ""):
        """
        This method is getting data from all switched devices and
        compares it with data from dS to ensure if a zone scene can be applied or
        only single device scene.
        """
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
            _event_type = "device"

            zone_devices = config.read_config_file()['zones']
            zones = ({v['id']: v for v in zone_devices})

            for event_entity_data in self.device_events.values():
                _zone_ids.append(event_entity_data["zoneid"])
                _applications.append(event_entity_data["application"])

            for event_zoneid in list(set(_zone_ids)):
                for _application in list(set(_applications)):
                    _v = []

                    if _application in CONTROL and "zone_scene" in CONTROL[_application]:
                        _d = list(value['dsuid'] for value in self.device_events.values())
                        _event_type = "zone" if all(elem in list(_d) for elem in
                                                    zones[event_zoneid]['applications'][_application]) else "device"

                    if _event_type == "zone":
                        for device in self.device_events.values():
                            _value = device['attributes'][CONTROL[_application]['id']]
                            if device['zoneid'] == event_zoneid:
                                if _application and device['application'] == _application:
                                    _v.append(_value)
                                    _v.sort()

                        _zone_scene = all(ele in (0, 100) for ele in _v)

                        # If zone is true but values are 0 or 100 patch zone
                        # otherwise fallback to single device control if all devices
                        # in same zone but values != 0 or 100
                        if _zone_scene:
                            action = CONTROL[_application]['zone_scene'][_v[0]]
                            self.event_patcher.patch_zone(zoneid, _application, action)
                        else:
                            _event_type = "device"

                    if _event_type == "device":
                        for device in self.device_events.values():
                            if device['application'] in ("absent", "manualState"):
                                if _application and device['application'] == _application:
                                    _value = device['attributes'][CONTROL[_application]['id']]
                                    self.event_patcher.patch_switch(
                                        device['dsuid'], CONTROL[_application]['device'][_value]
                                    )
                            else:
                                if device['zoneid'] == zoneid and _application and device['application'] == _application:
                                    if device['attributes'][CONTROL[_application]['id']] in CONTROL[_application][
                                            'device_scene'].keys():
                                        _value = device['attributes'][CONTROL[_application]['id']]
                                        action = CONTROL[_application]['device_scene'][_value]
                                        self.event_patcher.patch_device_scenario(
                                            device['dsuid'], action
                                        )
                                    else:
                                        self.event_patcher.patch_device_status(
                                            device['dsuid'], device['attributes']
                                        )

            self.hap_events = None
            self.device_events = {}
