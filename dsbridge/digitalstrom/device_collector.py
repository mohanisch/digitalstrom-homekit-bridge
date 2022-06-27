import time

from .const import DEVICES_CHARS, PROPERTY_API, SMART_HOME_API, HUE_DEVICES
from .helper import generate_dsuid
from .request_handler import DsRequest
from ..config import args, read_config_file as c


class DssCollector(object):
    """ Class to structure dS device and hold information of devices and it states """

    def __init__(self):
        self._devices = {}
        self._function_blocks = {}
        self._user_defined_states = {}
        self._submodules = {}
        self._zones = {}
        self._apartment = {}
        self._measurements = {}

        self._device_states = {}
        self.collected_zone = {}

        self.config_file = c()

        self.requesthandler = DsRequest("https://" + args.hostname + ":" + args.http_port + "/", self.config_file['token'])

    def collect_data(self, uri: str, api: str = SMART_HOME_API, params=None, key="data") -> list:
        if params is None:
            params = {}

        _response = self.requesthandler.get(api + uri, params=params)[key]
        return _response

    def gather_devices_status(self):
        devices_status_attributes = self.collect_data("/dsDevices/status")
        zones_status = self.collect_data("/zones/status")
        apartment_status = self.collect_data("/status")
        last_change = int(time.time())

        _apartment_states = {}
        _user_defined_states = {}
        _measurements = {}

        _dsuid = generate_dsuid(apartment_status['id'])

        _absent_state = apartment_status['attributes']['access']['absent']
        _entity_id = _dsuid + ".switch"
        _apartment_states[_entity_id] = {
            "state": "on" if _absent_state else "off",
            "last_change": last_change
        }

        for measurement, value in apartment_status['attributes']['measurements'].items():
            _service = measurement
            _value = value
            _entity_id = _dsuid + "." + _service
            _apartment_states[_entity_id] = {
                "states": {measurement: {"value": _value}},
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
                application = ({v['id']: v['attributes']['application'] for v in self._submodules}).get(device['id'])

                _entity_id = device['attributes']['functionBlocks'][0]['id'] + "." + str(application)
                d = {_entity_id: {
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
            _measurements = {device['entity_id']: {
                "states": _states,
                "last_change": last_change
            }}
            self._device_states.update(_measurements)

        ds = DsRequest("https://" + args.hostname + ":" + args.http_port + "/", self.config_file['token'])
        params = {
            "query": "/usr/addon-states/system-addon-user-defined-states/*(*)",
            "token": ds.get_token()
        }
        user_defined_states = self.collect_data("/query", PROPERTY_API, params=params,
                                                key="result")

        for user_state in user_defined_states['system-addon-user-defined-states']:
            _dsuid = generate_dsuid(user_state['name'])
            if user_state['type'] == 'custom-states' and user_state['showOnPhone']:
                _user_defined_states[_dsuid + ".manualState"] = {
                    "state": "on" if user_state['state'] == "active" else "off",
                    "last_change": last_change
                }
            self._device_states.update(_user_defined_states)
        return self._device_states

    def get_device_state(self, entity_id: str):
        _device_state = self._device_states[entity_id]
        return _device_state

    def get_entities(self, filter: bool = True):
        self._devices = self.collect_data("/dsDevices")
        self._function_blocks = self.collect_data("/functionBlocks")
        self._user_defined_states = self.collect_data("/userDefinedStates")
        self._submodules = self.collect_data("/submodules")

        self._transform_zones()
        self._transform_measurements()
        self._transform_output_devices()

        _devices = self._transform_output_devices() + \
                   self._transform_user_defined_states() + \
                   self._transform_measurements() + \
                   self._transform_apartment()
        if filter:
            self.gather_devices_status()
            if "devices" in self.config_file and "include" in self.config_file["devices"]:
                _devices = [x for x in _devices if x['entity_id'] in self.config_file["devices"]["include"]]

        return _devices

    def get_zone(self, zoneid: int):
        return ({int(v['id']): v for v in self._zones}).get(int(zoneid))

    def _transform_output_devices(self):
        _devices = []
        for device in self._devices:
            device_chars = []
            device_mode = ""
            device_support = {}

            function_attributes = ({v['id']: v['attributes'] for v in self._function_blocks}).get(device['id'])
            application = ({v['id']: v['attributes']['application'] for v in self._submodules}).get(device['id'])

            if 'outputs' in function_attributes:
                functions = {str(v['id']): v['attributes'] for v in function_attributes['outputs']}

                if application == "lights":
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
                        device_chars = DEVICES_CHARS[application][chars['attributes']['mode']]
                    device_mode = chars['attributes']['mode']

                zone = self.get_zone(device['attributes']['zone'])['name']
                d = {
                    "entity_id": device['id'] + "." + application,
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
        zones_status = self.collect_data("/zones/status")
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
                application = 'button'

                d = {
                    "entity_id": generate_dsuid(user_defined_state['id']) + "." + user_defined_state['type'],
                    "dsuid": generate_dsuid(user_defined_state['id']),
                    "name": user_defined_state['attributes']['name'],
                    "service": application,
                    "chars": None,
                    "support": None,
                    "zone": "Benutzerdefinierte Zustände",
                    "model": "Benutzerdefinierte Zustand"
                }
                _user_defined_states.append(d)
        return _user_defined_states

    def _transform_apartment(self):
        _apartment_states = []
        _apartment_data = []
        _apartment_data = self.collect_data("/status")

        _dsuid = generate_dsuid(_apartment_data['id'])
        for measurement in _apartment_data['attributes']['measurements']:
            d = {
                "entity_id": _dsuid + "." + measurement,
                "dsuid": _dsuid,
                "name": "Apartment " + measurement.capitalize(),
                "service": "sensor",
                "chars": [measurement.capitalize()],
                "support": None,
                "zone": "Apartment"
            }
            _apartment_states.append(d)

        d = {
            "entity_id": _dsuid + ".switch",
            "dsuid": _dsuid,
            "name": "Abwesenheit",
            "service": "button",
            "chars": None,
            "support": None,
            "zone": "Apartment"
        }
        _apartment_states.append(d)
        return _apartment_states

    def _transform_zones(self):
        zones = []
        zones_data = self.collect_data("/zones")

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
