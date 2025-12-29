from .. import device_collector
from ..acc import get_device_application
from ..const import DEVICES_CHARS, HUE_DEVICES


def get_device_function_attributes(device_id):
    return device_collector.get_device_function_attributes(device_id)


def get_zone(zoneid: int):
    return device_collector.get_zone(zoneid)


def get_devices():
    return device_collector.get_devices()


class OutputDevices:

    def __init__(self, data) -> None:
        super().__init__()
        self.data = data

    def gather_state(self, timestamp):
        _devices = {}
        for device in self.data:
            _device_application = get_device_application(device['id'])
            _entity_id = device['attributes']['functionBlocks'][0]['id'] + "." + str(_device_application)
            _states = {'on': False}
            _attributes = {}

            if "outputs" in device['attributes']['functionBlocks'][0]:
                for state in device['attributes']['functionBlocks'][0]['outputs']:
                    value = state['value'] if "value" in state else state['initialValue']
                    targetvalue = state['targetValue'] if "targetValue" in state else 0

                    if state['id'] in ('brightness', 'powerState'):
                        _states['on'] = bool(value)

                    _states[state['id']] = {
                        "value": value,
                        "targetvalue": targetvalue,
                    }

                    _attributes[state['id']] = value

                d = {_entity_id: {
                    "states": _states,
                    "attributes": _attributes,
                    "last_change": timestamp
                }}
                _devices.update(d)
        return _devices

    def entities(self):
        _devices = []
        for device in get_devices():
            device_chars = []
            device_mode = ""
            device_support = {}
            device_attributes = get_device_function_attributes(device['id'])
            device_application = get_device_application(device['id'])

            _technical_name = device_attributes['technicalName']

            if 'outputs' in device_attributes:
                functions = {str(v['id']): v['attributes'] for v in device_attributes['outputs']}

                if device_application == "lights":
                    if 'brightness' in functions:
                        device_support['brightness'] = functions['brightness']['mode'] == 'gradual'

                    device_support['colortemp'] = 'colortemp' in functions
                    device_support['saturation'] = 'saturation' in functions

                    if 'hue' in functions:
                        device_support['color'] = True
                        device_support['hue'] = device_attributes['technicalName'] in HUE_DEVICES
                    else:
                        device_support['color'] = False

                if device_application == "shades":
                    for chars in device_attributes['outputs']:
                        if chars['id'] in ['shadePositionOutside']:
                            device_chars = DEVICES_CHARS[device_application][chars['attributes']['mode']]
                        device_mode = chars['attributes']['mode']

                zone_obj = get_zone(device['attributes']['zone'])
                if zone_obj is None:
                    # Skip devices without valid zone
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning("Zone %s not found for device %s, skipping", device['attributes']['zone'],
                                   device['id'])
                    continue

                zone = zone_obj['name']
                d = {
                    "entity_id": device['id'] + "." + device_application,
                    "dsuid": device['id'],
                    "name": zone + " " + device['attributes']['name'],
                    "present": device['attributes']['present'],
                    "zoneid": device['attributes']['zone'],
                    "zone": zone,
                    "chars": device_chars,
                    "mode": device_mode,
                    "application": device_application,
                    "service": device_application,
                    "support": device_support,
                    "model": device_attributes['technicalName']
                }
                _devices.append(d)
        return _devices
