import time

from dsHomekit.digitalstrom import request_handler

if __name__ == '__main__':
    from const import DEVICES_CHARS
else:
    from .const import DEVICES_CHARS


class DssCollector(object):
    """ Class to structure dS device and hold information of devices and it states """

    def __init__(self):
        self._devices = request_handler.request("dsDevices")
        self._function_blocks = request_handler.request("functionBlocks")
        self._zones = request_handler.request("zones")['zones']
        self._submodules = request_handler.request("submodules")

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
                if 'hue' in functions:
                    device_support['color'] = True
                else:
                    device_support['color'] = False

                for chars in function_attributes['outputs']:
                    if chars['id'] in ['shadePositionOutside']:
                        device_chars = DEVICES_CHARS[device_type][chars['attributes']['mode']]
                    device_mode = chars['attributes']['mode']


                zone = ({int(v['id']): v['name'] for v in self._transform_zones()}).get(int(device['attributes']['zone']))
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
            device_support = {}

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
                                "support": None,
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

    bla = devices._transform_output_devices()
    #print(bla)
    print(json.dumps(bla,
                     sort_keys=True,
                     indent=4,
                     separators=(',', ': ')
                     ))
