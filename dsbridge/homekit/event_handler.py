"""
Event handler - optimized for performance
"""
import logging
from .const import CONTROL
from .. import config
from ..digitalstrom import event_patcher

logger = logging.getLogger(__name__)

# Cache for zone data to avoid frequent config reads
_zone_cache = None
_zone_cache_time = 0
_zone_cache_ttl = 30  # Cache zones for 30 seconds


def get_entity_by_aid(aid: int):
    """Returns entity_id by given aid - optimized with reverse lookup."""
    from . import homekit
    allocations = homekit.aid_storage.allocations
    
    # Create reverse lookup dict for O(1) access instead of O(n)
    if not hasattr(get_entity_by_aid, '_reverse_lookup'):
        get_entity_by_aid._reverse_lookup = {v: k for k, v in allocations.items()}
    
    return get_entity_by_aid._reverse_lookup.get(aid)


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
        self._zone_cache = None
        self._zone_cache_time = 0

    def receive_hap_event(self, events):
        """
        Getting events from HAP - optimized to use set for O(1) lookups.
        """
        _events = set()
        for event in events:
            if 'ev' in event:
                continue

            entity_id = get_entity_by_aid(event['aid'])
            if entity_id:  # Only add valid entity IDs
                _events.add(entity_id)
        
        self.hap_events = list(_events) if _events else None

    def device_event(self, entity_id: str, dsuid: str, zoneid: int, attributes: dict, application: str = ""):
        """
        This method is getting data from all switched devices and
        compares it with data from dS to ensure if a zone scene can be applied or
        only single device scene.
        """
        if self.hap_events is None:
            return  # No pending HAP events
        
        _count_hap_events = len(self.hap_events)
        
        # Only process if entity is in pending HAP events
        if entity_id not in self.hap_events:
            return
        
        # Add device event
        self.device_events[entity_id] = {
            "dsuid": dsuid,
            "zoneid": zoneid,
            "attributes": attributes,
            "application": application
        }
        
        _count_device_events = len(self.device_events)

        if _count_device_events == _count_hap_events:
            # Cache zone data to avoid frequent config reads
            import time
            current_time = time.time()
            if (self._zone_cache is None or 
                current_time - self._zone_cache_time > 30):  # Cache for 30 seconds
                try:
                    zone_devices = config.read_config_file().get('zones', [])
                    self._zone_cache = {str(v['id']): v for v in zone_devices}
                    # Add Zone 0 as special zone for apartment devices (e.g., outside temp, absence)
                    # Zone 0 doesn't support zone scenes, only device events
                    if '0' not in self._zone_cache:
                        self._zone_cache['0'] = {
                            'id': 0,
                            'name': 'Apartment',
                            'applications': {}
                        }
                    self._zone_cache_time = current_time
                except Exception as e:
                    logger.error("Error loading zone cache: %s", e, exc_info=True)
                    self._zone_cache = {}
                    # Ensure Zone 0 exists even if config loading fails
                    self._zone_cache['0'] = {
                        'id': 0,
                        'name': 'Apartment',
                        'applications': {}
                    }
            
            zones = self._zone_cache
            
            # Collect unique zone IDs and applications
            _zone_ids = set()
            _applications = set()
            for event_data in self.device_events.values():
                _zone_ids.add(event_data["zoneid"])
                _applications.add(event_data["application"])

            # Process each zone/application combination
            for event_zoneid in _zone_ids:
                zone_key = str(event_zoneid)
                if zone_key not in zones:
                    logger.warning("Zone %s not found in cache", event_zoneid)
                    continue
                    
                for _application in _applications:
                    if not _application or _application not in CONTROL:
                        continue
                    
                    control_config = CONTROL[_application]
                    if "zone_scene" not in control_config:
                        _event_type = "device"
                    elif event_zoneid == 0:
                        # Zone 0 (Apartment) doesn't support zone scenes, only device events
                        _event_type = "device"
                    else:
                        # Check if all devices in zone are part of this event
                        zone_app_devices = zones[zone_key].get('applications', {}).get(_application, [])
                        event_dsuids = {d['dsuid'] for d in self.device_events.values() 
                                       if d['zoneid'] == event_zoneid and d['application'] == _application}
                        
                        # Only use zone scene if zone has devices configured and all are in event
                        _event_type = "zone" if (zone_app_devices and event_dsuids and 
                                                 set(zone_app_devices).issubset(event_dsuids)) else "device"

                    if _event_type == "zone":
                        # Collect values for zone scene check
                        _values = []
                        control_id = control_config['id']
                        
                        for device in self.device_events.values():
                            if (device['zoneid'] == event_zoneid and 
                                device['application'] == _application and
                                control_id in device['attributes']):
                                _values.append(device['attributes'][control_id])
                        
                        _values.sort()
                        _zone_scene = all(v in (0, 100) for v in _values)

                        if _zone_scene and _values:
                            action = control_config['zone_scene'][_values[0]]
                            self.event_patcher.patch_zone(event_zoneid, _application, action)
                        else:
                            _event_type = "device"

                    if _event_type == "device":
                        # Process each device individually
                        control_id = control_config['id']
                        for device in self.device_events.values():
                            if device['zoneid'] != event_zoneid or device['application'] != _application:
                                continue
                                
                            if device['application'] in ("absent", "manualState"):
                                if control_id in device['attributes']:
                                    _value = device['attributes'][control_id]
                                    if 'device' in control_config and _value in control_config['device']:
                                        self.event_patcher.patch_switch(
                                            device['dsuid'], control_config['device'][_value]
                                        )
                            else:
                                if control_id in device['attributes']:
                                    _value = device['attributes'][control_id]
                                    if 'device_scene' in control_config and _value in control_config['device_scene']:
                                        action = control_config['device_scene'][_value]
                                        self.event_patcher.patch_device_scenario(device['dsuid'], action)
                                    else:
                                        self.event_patcher.patch_device_status(device['dsuid'], device['attributes'])

            # Reset for next batch
            self.hap_events = None
            self.device_events = {}
