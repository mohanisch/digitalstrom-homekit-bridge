import time

from dsHomekit.digitalstrom import request_handler
from .const import DEVICES_CHARS


class DssCollector(object):
    """ Class to structure dS device and hold information of devices and it states """

    def __init__(self):
        self._devices = request_handler.request("dsDevices")
        self._function_blocks = request_handler.request("functionBlocks")
        self._zones = request_handler.request("zones")['zones']

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
        return self._transform_output_devices() + self._transform_input_devices()

    def _transform_output_devices(self):
        _devices = []
        for device in self._devices:
            function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(device['id'])
            device_chars = []
            device_mode = ""
            device_type = ""

            if 'outputs' in function_attributes:
                for chars in function_attributes['outputs']:
                    if chars['id'] in ['hue', 'saturation', 'brightness']:
                        device_chars.append(chars['id'].capitalize())
                        device_type = "light"
                    if chars['id'] in ['shadePositionOutside']:
                        device_type = "windowcover"
                        device_chars = DEVICES_CHARS[device_type][chars['attributes']['mode']]
                    device_mode = chars['attributes']['mode']

            if device_type == "light":
                device_chars.append('On')

            zone = ({int(v['id']): v['name'] for v in self._transform_zones()}).get(int(device['attributes']['zone']))
            if device_type:
                d = {
                    "entity_id": device['id'] + "." + device_type,
                    "dsuid": device['id'],
                    "name": zone + " " + device['attributes']['name'],
                    "present": device['attributes']['present'],
                    "zoneid": device['attributes']['zone'],
                    "zone": zone,
                    "chars": device_chars,
                    "mode": device_mode,
                    "service": device_type,
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

                    if 'type' in chars['attributes']:
                        device_chars.append(chars['attributes']['type'].capitalize())
                        device_type = chars['attributes']['type']

                        zone = ({int(v['id']): v['name'] for v in self._transform_zones()}).get(int(device['attributes']['zone']))
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
                                "service": 'sensor',
                                "model": function_attributes['technicalName']
                            }
                            _input_devices.append(s)
        return _input_devices

    def gather_devices_status(self):
        devices_status_attributes = request_handler.request("dsDevices/status")
        zones_status = request_handler.request("zones/status")
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
                zone_measurements = ({v['id']: v for v in zones_status}).get(device['zoneid'])['attributes']['measurements']

                for dsuid, value in zone_measurements.items():
                    _states[dsuid] = {
                        "value": value,
                    }
                s = {device['dsuid']: {
                    "states": _states,
                }}
                self._device_states.update(s)
        return self._device_states

    def _transform_zones(self):
        zones = []

        for zone in self._zones:
            if "name" in zone["attributes"]:
                cleaned = {
                    "id": zone["id"],
                    "name": zone["attributes"]["name"]
                }
                zones.append(cleaned)
        return zones


if __name__ == '__main__':
    devices = DssCollector()
    import json

    bla = devices.gather_devices_status()
    print(bla)
    print(json.dumps(bla,
                     sort_keys=True,
                     indent=4,
                     separators=(',', ': ')
                     ))
