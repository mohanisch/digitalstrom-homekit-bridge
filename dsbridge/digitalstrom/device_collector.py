import time

from .const import DEVICES_CHARS, SMART_HOME_API, HUE_DEVICES, DEVICE_SUPPORT
from .helper import generate_dsuid
from .request_handler import DsRequest
from ..config import args, read_config_file as c


class DssCollector(object):
    """ Class to structure dS device and hold information of devices, and it states """

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

        self.request_handler = DsRequest("https://" + args.dss_hostname + ":" + args.dss_http_port + "/",
                                         self.config_file['token'])

        # TODO: imports have to be restructured
        self.apartment_data = self.collect_data("/", params={"include": "dsDevices,functionBlocks,userDefinedStates,submodules,zones"})
        self._function_blocks = self.apartment_data['included']['functionBlocks']
        self._submodules = self.apartment_data['included']['submodules']
        self._transform_zones(self.apartment_data['included']['zones'])

    def collect_data(self, uri: str, api: str = SMART_HOME_API, params=None, key="data"):
        if params is None:
            params = {}

        _response = self.request_handler.get(api + uri, params=params)[key]
        return _response

    def gather_devices_status(self):
        apartment = self.collect_data("/status", params={"include": "dsDevices,zones,userDefinedStates"})
        apartment_status = apartment['included']

        zones_status = apartment_status['zones']
        last_change = int(time.time())

        _measurements = {}

        from .acc import Apartment, UserDefinedStates, OutputDevices
        apartment = Apartment(apartment['id'], apartment['attributes'])
        self._device_states.update(apartment.gather_state(last_change))

        user_defined_states = UserDefinedStates(apartment_status['userDefinedStates'])
        self._device_states.update(user_defined_states.gather_state(last_change))

        output_devices = OutputDevices(apartment_status['dsDevices'])
        self._device_states.update(output_devices.gather_state(last_change, self._submodules))

        for device in zones_status:
            if self.get_zone(device['id']) and 'attributes' in device and 'measurements' in device['attributes']:
                _dsuid = generate_dsuid(device['id'])
                _states = {}
                zone_attributes = ({v['id']: v for v in zones_status}).get(device['id'])['attributes']

                zone_measurements = zone_attributes['measurements']

                for measurement, value in zone_measurements.items():
                    entity_id = _dsuid + "." + measurement
                    _states[measurement] = {
                        "value": value,
                    }
                    _measurements = {entity_id: {
                        "states": _states,
                        "last_change": last_change
                    }}
                    self._device_states.update(_measurements)

        return self._device_states

    def get_device_state(self, entity_id: str):
        return self._device_states[entity_id]

    def get_entities(self):
        self._devices = self.apartment_data['included']['dsDevices']
        self._function_blocks = self.apartment_data['included']['functionBlocks']
        self._user_defined_states = self.apartment_data['included']['userDefinedStates']
        self._submodules = self.apartment_data['included']['submodules']

        _devices = self._transform_output_devices() + \
                   self._transform_user_defined_states() + \
                   self._transform_measurements() + \
                   self._transform_apartment()

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

            _technical_name = function_attributes['technicalName']

            if 'outputs' in function_attributes:
                functions = {str(v['id']): v['attributes'] for v in function_attributes['outputs']}

                if _technical_name in DEVICE_SUPPORT:
                    for _attr in DEVICE_SUPPORT[_technical_name]['support']:
                        device_support[_attr] = True
                else:
                    if application == "lights":
                        if 'brightness' in functions:
                            device_support['brightness'] = True if functions['brightness'][
                                                                       'mode'] == 'gradual' else False

                        device_support['colortemp'] = True if 'colortemp' in functions else False

                        if 'hue' in functions:
                            device_support['color'] = True
                            device_support['hue'] = True if function_attributes[
                                                                'technicalName'] in HUE_DEVICES else False

                        else:
                            device_support['color'] = False

                if application == "shades":
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
                    "application": application,
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
            if self.get_zone(zone['id']) and 'attributes' in zone and 'measurements' in zone['attributes']:
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
                        "application": measurement,
                        "service": 'sensor',
                    }
                    _measurements.append(m)
        return _measurements

    def _transform_user_defined_states(self):
        from .acc import UserDefinedStates
        data = self._user_defined_states
        user_defined_states = UserDefinedStates(data)
        return user_defined_states.get_entities()

    def _transform_apartment(self):
        from .acc import Apartment
        data = self.collect_data("/status")
        apartment = Apartment(data['id'], data['attributes'])
        return apartment.get_entities()

    def _transform_zones(self, data):
        zones = []
        zones_data = data

        for zone in zones_data:

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
