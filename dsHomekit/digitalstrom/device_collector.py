import json
import time
from typing import Any
from .const import DEVICES_CHARS, PROPERTY_API, SMART_HOME_API, HUE_DEVICES
from ..config import file as configfile
from ..utils.helper import generate_dsuid


def collect_data(uri: str, data_filter: str = "") -> list:
    from dsHomekit.digitalstrom import dsrequest
    _response = dsrequest.get(SMART_HOME_API + uri)['data']

    if (
            data_filter == "devices" and
            configfile is not None and
            "devices" in configfile
    ):
        _filtered_response = Any
        if "include" in configfile["devices"]:
            _filtered_response = [x for x in _response if x['id'] in configfile["devices"]["include"]]
        if "exclude" in configfile["devices"]:
            _filtered_response = [x for x in _response if x['id'] not in configfile["devices"]["exclude"]]
        return _filtered_response
    else:
        return _response


class DssCollector(object):
    """ Class to structure dS device and hold information of devices and it states """

    def __init__(self):
        self._devices = collect_data("/dsDevices", "devices")
        self._function_blocks = collect_data("/functionBlocks")
        self._user_defined_states = collect_data("/userDefinedStates")
        self._submodules = collect_data("/submodules")
        self._zones = {}
        self._apartment = {}
        self._measurements = {}

        self._device_states = {}
        self.collected_zone = {}

        self._transform_zones()
        self._transform_measurements()
        self._transform_output_devices()

        self.gather_devices_status()

    def gather_devices_status(self):
        devices_status_attributes = collect_data("/dsDevices/status")
        zones_status = collect_data("/zones/status")
        apartment_status = collect_data('/status')['attributes']
        last_change = int(time.time())

        _apartment_states = {}
        if 'absent' in configfile and configfile['absent']:
            _absent_state = apartment_status['access']['absent']
            _apartment_states['apartmentAbsents'] = {
                "state": "on" if _absent_state else "off",
                "last_change": last_change
            }
        _apartment_temperature = apartment_status['measurements']['temperature']
        _apartment_states['apartmentMeasurementsTemperature'] = {
            "states": {"temperature": {"value": _apartment_temperature}},
            "last_change": last_change
        }
        self._device_states.update(_apartment_states)

        for device in devices_status_attributes:
            if "outputs" in device['attributes']['functionBlocks'][0]:
                _states = {}
                _attributes = {}
                for state in device['attributes']['functionBlocks'][0]['outputs']:
                    targetvalue = state['targetValue'] if "targetValue" in state else 0
                    value = state['value'] if "value" in state else state['initialValue']

                    _states[state['id']] = {
                        "value": value,
                        "targetvalue": targetvalue,
                    }
                    _states['on'] = True if state['id'] == 'brightness' and value > 0 else False
                    _attributes[state['id']] = value

                d = {device['attributes']['functionBlocks'][0]['id']: {
                    "states": _states,
                    "attributes": _attributes,
                    "last_change": last_change
                }}
                self._device_states.update(d)

        for device in self._transform_measurements():
            _states = {}
            zone_attributes = ({v['id']: v for v in zones_status}).get(device['zoneid'])['attributes']
            _dsuid = generate_dsuid(device['dsuid'])

            zone_measurements = zone_attributes['measurements']
            for dsuid, value in zone_measurements.items():
                _states[dsuid] = {
                    "value": value,
                }
            s = {device['dsuid']: {
                "states": _states,
                "last_change": last_change
            }}
            self._device_states.update(s)

        from dsHomekit.digitalstrom import dsrequest
        params = {
            "query": "/usr/addon-states/system-addon-user-defined-states/*(*)",
            "token": dsrequest.get_token()
        }
        user_defined_states = dsrequest.get(PROPERTY_API + "/query", params=params)['result']
        _user_defined_states = {}
        for user_state in user_defined_states['system-addon-user-defined-states']:
            _user_defined_states[user_state['name']] = {
                "state": "on" if user_state['state'] == "active" else "off",
                "last_change": last_change
            }
        self._device_states.update(_user_defined_states)

        return self._device_states

    def get_device_state(self, dsuid: str):
        _device_state = self._device_states[dsuid]
        return _device_state

    def get_entities(self):
        return self._transform_output_devices() + \
               self._transform_user_defined_states() + \
               self._transform_measurements() + \
               self._transform_apartment()

    def get_zone(self, zoneid: int):
        return ({int(v['id']): v for v in self._zones}).get(int(zoneid))

    def _transform_output_devices(self):
        _devices = []
        for device in self._devices:
            function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(device['id'])
            application = ({v['id']: v['attributes']['application'] for v in self._submodules}).get(device['id'])
            device_chars = []
            device_mode = ""
            device_type = application
            device_support = {}

            if 'outputs' in function_attributes:
                functions = (
                    {str(v['id']): v['attributes'] for v in function_attributes['outputs']}
                )
                if 'brightness' in functions:
                    device_support['brightness'] = True if functions['brightness']['mode'] == 'gradual' else False

                device_support['colortemp'] = True if 'colortemp' in functions else False

                if 'hue' in functions:
                    device_support['color'] = True
                    device_support['hue'] = True if function_attributes['technicalName'] in HUE_DEVICES else False

                else:
                    device_support['color'] = False

                for chars in function_attributes['outputs']:
                    if chars['id'] in ['shadePositionOutside']:
                        device_chars = DEVICES_CHARS[device_type][chars['attributes']['mode']]
                    device_mode = chars['attributes']['mode']

                zone = self.get_zone(device['attributes']['zone'])['name']
                d = {
                    "entity_id": device['id'] + "." + device_type,
                    "dsuid": device['id'],
                    "name": zone + " " + device['attributes']['name'],
                    "present": device['attributes']['present'],
                    "zoneid": device['attributes']['zone'],
                    "zone": zone,
                    "chars": device_chars,
                    "mode": device_mode,
                    "service": application,
                    "support": device_support,
                    "model": function_attributes['technicalName']
                }
                _devices.append(d)
        return _devices

    def _transform_measurements(self):
        zones_status = collect_data("/zones/status")
        _measurements = []

        for zone in zones_status:
            if self.get_zone(zone['id']) and 'measurements' in zone['attributes']:
                zone_name = self.get_zone(zone['id'])['name']

                for measurement in zone['attributes']['measurements']:
                    _dsuid = generate_dsuid(zone['id'])
                    m = {
                        "entity_id": _dsuid + "." + measurement,
                        "dsuid": _dsuid,
                        "name": zone_name + " " + measurement,
                        "zoneid": zone['id'],
                        "zone": zone_name,
                        "chars": [measurement.capitalize()],
                        "support": None,
                        "service": 'sensor',
                    }
                    _measurements.append(m)
        return _measurements

    def _transform_user_defined_states(self):
        _user_defined_states = []

        for user_defined_state in self._user_defined_states['userDefinedStates']:
            if user_defined_state['type'] == 'manualState' and user_defined_state['attributes']['visibleForUsers']:
                device_type = 'button'

                d = {
                    "entity_id": user_defined_state['id'] + "." + user_defined_state['type'],
                    "dsuid": user_defined_state['id'],
                    "name": user_defined_state['attributes']['name'],
                    "service": device_type,
                    "chars": None,
                    "support": None,
                }
                _user_defined_states.append(d)
        return _user_defined_states

    def _transform_apartment(self):
        _apartment_states = []

        if 'absent' in configfile and configfile['absent']:
            d = {
                "entity_id": "apartmentAbsents.switch",
                "dsuid": "apartmentAbsents",
                "name": "apartmentAbsents",
                "service": "button",
                "chars": None,
                "support": None,
            }
            _apartment_states.append(d)
            d = {
                "entity_id": "apartmentMeasurementsTemperature.sensor",
                "dsuid": "apartmentMeasurementsTemperature",
                "name": "apartmentMeasurementsTemperature",
                "service": "sensor",
                "chars": ["Temperature"],
                "support": None,
            }
            _apartment_states.append(d)

        return _apartment_states

    def _transform_zones(self):
        zones = []
        zones_data = collect_data("/zones")

        for zone in zones_data['zones']:  # self._zones:

            _applications = {}
            if zone['id'] != '65534':
                for application in zone['attributes']['applications']:
                    _applications[application] = []

                for submodule in zone["attributes"]["submodules"]:
                    function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(submodule)
                    if "outputs" in function_attributes:
                        submodule_applications = (
                            {v['id']: v['attributes']['application'] for v in self._submodules}).get(submodule)
                        _applications[submodule_applications].append(submodule)

            if "name" in zone["attributes"] and zone["id"] != 65534:
                cleaned = {
                    "id": zone["id"],
                    "name": zone["attributes"]["name"],
                    "devices": _applications
                }
                zones.append(cleaned)
        self._zones = zones
