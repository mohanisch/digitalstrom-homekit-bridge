from .const import SMART_HOME_API
import time

from .helper import generate_dsuid
from .request_handler import RequestHandler
from ..config import args, read_config_file as c


def collect_data(uri: str, api: str = SMART_HOME_API, params=None, key="data"):
    request_handler = RequestHandler("https://" + args.dss_hostname + ":" + args.dss_http_port, c()['token'])
    if params is None:
        params = {}

    _response = request_handler.get(api + uri, params=params)[key]
    return _response


class DssStateCollector(object):
    def __init__(self):
        self._device_states = {}

    def get_device_state(self, entity_id: str):
        return self._device_states[entity_id]

    def gather_devices_status(self):
        apartment = collect_data("/status", params={"include": "dsDevices,zones,userDefinedStates"})
        apartment_status = apartment['included']

        zones_status = apartment_status['zones']
        last_change = int(time.time())

        _measurements = {}

        from .acc.user_defined_states import UserDefinedStates
        from .acc.apartment import Apartment
        from .acc.output_devices import OutputDevices

        apartment_states = Apartment(apartment['id'], apartment['attributes'])
        self._device_states.update(apartment_states.gather_state(last_change))

        user_defined_states = UserDefinedStates(apartment_status['userDefinedStates'])
        self._device_states.update(user_defined_states.gather_state(last_change))

        output_devices = OutputDevices(apartment_status['dsDevices'])
        self._device_states.update(output_devices.gather_state(last_change))

        for device in zones_status:
            if 'attributes' in device and 'measurements' in device['attributes']:
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


class DssCollector(object):
    """ Class to structure dS device and hold information of devices """

    def __init__(self):
        self.apartment_data = None
        self._zones = {}
        self._apartment = {}
        self._measurements = {}
        self.collected_zone = {}

        # TODO: imports have to be restructured
        self._devices = {}
        self._function_blocks = {}
        self._user_defined_states = {}
        self._submodules = {}

        self.load_apartment_data()

    def load_apartment_data(self):
        self.apartment_data = collect_data("/", params={
            "include": "dsDevices,functionBlocks,userDefinedStates,submodules,zones"})
        self._devices = self.apartment_data['included']['dsDevices']
        self._function_blocks = self.apartment_data['included']['functionBlocks']
        self._user_defined_states = self.apartment_data['included']['userDefinedStates']
        self._submodules = self.apartment_data['included']['submodules']
        self._transform_zones(self.apartment_data['included']['zones'])

    def get_entities(self):
        _devices = self._transform_output_devices() + \
                   self._transform_user_defined_states() + \
                   self._transform_measurements() + \
                   self._transform_apartment()

        return _devices

    def get_devices(self):
        return self._devices

    def get_zone(self, zoneid: int):
        return ({int(v['id']): v for v in self._zones}).get(int(zoneid))

    def get_device_application(self, device_id):
        return ({v['id']: v['attributes']['application'] for v in self._submodules}).get(device_id)

    def get_device_function_attributes(self, device_id):
        return ({v['id']: v['attributes'] for v in self._function_blocks}).get(device_id)

    def _transform_output_devices(self):
        from .acc.output_devices import OutputDevices
        output_devices = OutputDevices(self._devices)
        return output_devices.entities()

    def _transform_measurements(self):
        zones_status = collect_data("/zones/status")
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
        from .acc.user_defined_states import UserDefinedStates
        data = self._user_defined_states
        user_defined_states = UserDefinedStates(data)
        return user_defined_states.get_entities()

    def _transform_apartment(self):
        from .acc.apartment import Apartment
        data = collect_data("/status")
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
