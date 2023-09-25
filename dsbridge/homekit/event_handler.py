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
    def __init__(self):
        self.hap_events = None
        self.device_events = {}

        self.ep = event_patcher

    def receive_hap_event(self, events):
        _events = {}
        for event in events:
            if 'ev' in event:
                continue

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
            _event_type = "device"

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

                    if _application in CONTROL and "zone_scene" in CONTROL[_application]:
                        _d = []
                        for k, v in self.device_events.items():
                            _d.append(v['dsuid'])

                        _event_type = "zone" if all(
                            elem in list(_d) for elem in
                            zones[zoneid]['applications'][_application]) else "device"

                    if _event_type == "zone":
                        for e, a in self.device_events.items():
                            _value = a['attributes'][CONTROL[_application]['id']]
                            if a['zoneid'] == zoneid:
                                if _application and a['application'] == _application:
                                    _v.append(_value)
                                    _v.sort()
                        _zone_scene = all(0 == ele or ele == 100 for ele in _v)

                        if not _zone_scene:
                            _event_type = "device"
                        else:
                            action = CONTROL[_application]['zone_scene'][_v[0]]
                            self.ep.patch_zone(zoneid, _application, action)

                    if _event_type == "device":
                        for e, a in self.device_events.items():
                            if a['application'] in ("absent", "manualState"):
                                if _application and a['application'] == _application:
                                    _value = a['attributes'][CONTROL[_application]['id']]
                                    self.ep.patch_switch(
                                        a['dsuid'], CONTROL[_application]['device'][_value]
                                    )
                            else:
                                if a['zoneid'] == zoneid:
                                    if _application and a['application'] == _application:
                                        if a['attributes'][CONTROL[_application]['id']] in CONTROL[_application][
                                                'device_scene'].keys():
                                            _value = a['attributes'][CONTROL[_application]['id']]
                                            action = CONTROL[_application]['device_scene'][_value]
                                            self.ep.patch_device_scenario(
                                                a['dsuid'], action
                                            )
                                        else:
                                            self.ep.patch_device_status(
                                                a['dsuid'], a['attributes']
                                            )

            self.clean_events()

    def _action(self, action):
        return all(value['action'] == action for value in self.device_events.values())

    def clean_events(self):
        self.hap_events = None
        self.device_events = {}
