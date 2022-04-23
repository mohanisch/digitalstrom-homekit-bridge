import time
from typing import Any

import yaml
from .const import DEVICES_CHARS, PROPERTY_API, SMART_HOME_API, HUE_DEVICES
from ..config import args

with open(args.config_path + "/config.yml", "r") as stream:
    try:
        dsconfig_file = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)


def collect_data(uri, data_filter: str = ""):
    from dsHomekit.digitalstrom import dsrequest
    _response = dsrequest.get(SMART_HOME_API + uri)['data']

    _data = Any
    if data_filter == "devices" and "devices" in dsconfig_file:
        if "include" in dsconfig_file["devices"]:
            _data = [x for x in _response if x['id'] in dsconfig_file["devices"]["include"]]
            return _data
    else:
        return _response


class DssCollector(object):
    """ Class to structure dS device and hold information of devices and it states """

    def __init__(self):
        from dsHomekit.digitalstrom import dsrequest
        self._devices = collect_data("/dsDevices", "devices")
        self._function_blocks = dsrequest.get(SMART_HOME_API + "/functionBlocks")['data']
        self._zones = {}
        self._submodules = dsrequest.get(SMART_HOME_API + "/submodules")['data']
        self._user_defined_states = dsrequest.get(SMART_HOME_API + "/userDefinedStates")['data']['userDefinedStates']

        self._device_states = {}
        self.collected_zone = {}

        self._transform_zones()
        self._transform_output_devices()
        self._transform_input_devices()

        self.gather_devices_status()

    def get_device_state(self, dsuid: str):
        _device_state = self._device_states[dsuid]
        return _device_state

    def get_devices(self):
        return self._transform_output_devices() + self._transform_input_devices() + self._transform_user_defined_states()

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

    def _transform_input_devices(self):
        _input_devices = []

        for device in self._devices:
            function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(device['id'])
            device_mode = ""

            if 'sensorInputs' in function_attributes:
                for chars in function_attributes['sensorInputs']:
                    device_chars = []

                    if 'type' in chars['attributes'] and chars['attributes']['usage'] == 'zone':
                        device_chars.append(chars['attributes']['type'].capitalize())
                        device_type = chars['attributes']['type']

                        zone = self.get_zone(device['attributes']['zone'])['name']
                        if device_type:
                            s = {
                                "entity_id": device['id'] + "." + device_type,
                                "dsuid": device['id'],
                                "name": zone + " " + device['attributes']['name'],
                                "present": device['attributes']['present'],
                                "zoneid": device['attributes']['zone'],
                                "zone": zone,
                                "chars": device_chars,
                                "mode": device_mode,
                                "support": None,
                                "service": 'sensor',
                                "model": function_attributes['technicalName']
                            }
                            _input_devices.append(s)
        return _input_devices

    def _transform_user_defined_states(self):
        _user_defined_states = []

        for user_defined_state in self._user_defined_states:
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

    def gather_devices_status(self):
        from dsHomekit.digitalstrom import dsrequest
        devices_status_attributes = dsrequest.get(SMART_HOME_API + "/dsDevices/status")['data']
        zones_status = dsrequest.get(SMART_HOME_API + "/zones/status")['data']

        params = {
            "query": "/usr/addon-states/system-addon-user-defined-states/*(*)",
            "token": dsrequest.get_token()
        }
        user_defined_states = dsrequest.get(PROPERTY_API + "/query", params=params)['result']

        last_change = int(time.time())

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

        for device in self._transform_input_devices():
            if device['service'] == 'sensor':
                _states = {}

                zone_attributes = ({v['id']: v for v in zones_status}).get(device['zoneid'])['attributes']
                if 'measurements' in zone_attributes:
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

        _user_defined_states = {}
        for user_state in user_defined_states['system-addon-user-defined-states']:
            _user_defined_states[user_state['name']] = {
                "state": "on" if user_state['state'] == "active" else "off",
                "last_change": last_change
            }
        self._device_states.update(_user_defined_states)

        return self._device_states

    def _transform_zones(self):
        zones = []
        zones_data = collect_data("/zones")

        for zone in zones_data['zones']:  # self._zones:

            _applications = {}
            if zone['id'] == '28313':
                for application in zone['attributes']['applications']:
                    _applications[application] = []

                for submodule in zone["attributes"]["submodules"]:
                    function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(submodule)
                    if "outputs" in function_attributes:
                        submodule_applications = ({v['id']: v['attributes']['application'] for v in self._submodules}).get(submodule)
                        _applications[submodule_applications].append(submodule)

            if "name" in zone["attributes"] and zone["id"] != 65534:
                cleaned = {
                    "id": zone["id"],
                    "name": zone["attributes"]["name"],
                    "devices": _applications
                }
                zones.append(cleaned)
        self._zones = zones

# #if __name__ == '__main__':
# devices = DssCollector()
# import json
#
# bla = devices.gather_devices_status()
# #print(bla)
# print(json.dumps(bla,
#                  sort_keys=True,
#                  indent=4,
#                  separators=(',', ': ')
#                  ))
