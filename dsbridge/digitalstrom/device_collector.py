import logging
import time
from .const import SMART_HOME_API
from .helper import generate_dsuid
from .request_handler import RequestHandler
from ..config import args, read_config_file as c

logger = logging.getLogger(__name__)


# Request handler cache to avoid recreating sessions
_request_handler_cache = None
_request_handler_token = None


def collect_data(uri: str, api: str = SMART_HOME_API, params=None, key="data"):
    """
    Collect data from digitalStrom API with error handling and connection reuse.
    
    Args:
        uri: API endpoint URI
        api: API base path
        params: Query parameters
        key: Key to extract from response
        
    Returns:
        Data from response[key]
        
    Raises:
        KeyError: If key not found in response
        requests.exceptions.RequestException: If API request fails
    """
    global _request_handler_cache, _request_handler_token
    
    try:
        config = c()
        if 'token' not in config or not config['token']:
            raise ValueError("No token found in configuration")
        
        # Reuse request handler if token hasn't changed (connection pooling)
        if (_request_handler_cache is None or 
            _request_handler_token != config['token']):
            _request_handler_cache = RequestHandler(
                "https://" + args.dss_hostname + ":" + args.dss_http_port,
                config['token']
            )
            _request_handler_token = config['token']
        
        request_handler = _request_handler_cache
        
        if params is None:
            params = {}

        _response = request_handler.get(api + uri, params=params)
        
        if key not in _response:
            logger.error("Key '%s' not found in API response for %s", key, uri)
            raise KeyError(f"Key '{key}' not found in response")
            
        return _response[key]
    except Exception as e:
        logger.error("Error collecting data from %s: %s", uri, e, exc_info=True)
        raise


class DssStateCollector:
    def __init__(self):
        self._device_states = {}

    def get_device_state(self, entity_id: str):
        """
        Get device state with error handling.
        
        Args:
            entity_id: Entity ID to look up
            
        Returns:
            Device state dictionary
            
        Raises:
            KeyError: If entity_id not found
        """
        if entity_id not in self._device_states:
            logger.warning("Device state not found for entity_id: %s", entity_id)
            # Return empty state structure to prevent crashes
            return {
                'states': {},
                'attributes': {},
                'last_change': 0
            }
        return self._device_states[entity_id]

    def gather_devices_status(self):
        """Gather device statuses from digitalStrom API with error handling."""
        try:
            apartment = collect_data("/status", params={"include": "dsDevices,zones,userDefinedStates"})
            
            if 'included' not in apartment:
                logger.error("Unexpected apartment status structure: missing 'included' key")
                return self._device_states
                
            apartment_status = apartment['included']
            zones_status = apartment_status.get('zones', [])
            last_change = int(time.time())

            _measurements = {}

            from .acc.user_defined_states import UserDefinedStates
            from .acc.apartment import Apartment
            from .acc.output_devices import OutputDevices

            try:
                apartment_states = Apartment(apartment['id'], apartment['attributes'])
                self._device_states.update(apartment_states.gather_state(last_change))
            except Exception as e:
                logger.error("Error gathering apartment states: %s", e, exc_info=True)

            try:
                user_defined_states = UserDefinedStates(apartment_status.get('userDefinedStates', []))
                self._device_states.update(user_defined_states.gather_state(last_change))
            except Exception as e:
                logger.error("Error gathering user defined states: %s", e, exc_info=True)

            try:
                output_devices = OutputDevices(apartment_status.get('dsDevices', []))
                self._device_states.update(output_devices.gather_state(last_change))
            except Exception as e:
                logger.error("Error gathering output device states: %s", e, exc_info=True)

            # Optimize zone processing with dictionary lookup
            zones_dict = {str(v['id']): v for v in zones_status}
            
            for device_id, device in zones_dict.items():
                try:
                    if 'attributes' in device and 'measurements' in device['attributes']:
                        _dsuid = generate_dsuid(device_id)
                        zone_measurements = device['attributes'].get('measurements', {})

                        for measurement, value in zone_measurements.items():
                            entity_id = _dsuid + "." + measurement
                            _states = {measurement: {"value": value}}
                            _measurements = {entity_id: {
                                "states": _states,
                                "last_change": last_change
                            }}
                            self._device_states.update(_measurements)
                except Exception as e:
                    logger.error("Error processing zone device %s: %s", device_id, e, exc_info=True)

            return self._device_states
        except Exception as e:
            logger.error("Fatal error gathering device status: %s", e, exc_info=True)
            return self._device_states


class DssCollector:
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

        # Try to load apartment data, but don't fail if token is not available yet
        try:
            self.load_apartment_data()
        except Exception as e:
            logger.debug("Could not load apartment data during initialization: %s", e)
            # Set defaults to prevent further errors
            self._devices = []
            self._function_blocks = []
            self._user_defined_states = []
            self._submodules = []
            self._zones = []

    @property
    def submodules(self):
        return self._submodules

    @submodules.setter
    def submodules(self, value):
        self._submodules = value

    def load_apartment_data(self):
        """Load apartment data from digitalStrom API with error handling."""
        try:
            self.apartment_data = collect_data("/", params={
                "include": "dsDevices,functionBlocks,userDefinedStates,submodules,zones"})
            
            if 'included' not in self.apartment_data:
                logger.error("Unexpected apartment data structure: missing 'included' key")
                return
                
            included = self.apartment_data['included']
            self._devices = included.get('dsDevices', [])
            self._function_blocks = included.get('functionBlocks', [])
            self._user_defined_states = included.get('userDefinedStates', [])
            self._submodules = included.get('submodules', [])
            
            zones = included.get('zones', [])
            self._transform_zones(zones)
        except Exception as e:
            logger.error("Error loading apartment data: %s", e, exc_info=True)
            # Set defaults to prevent further errors
            self._devices = []
            self._function_blocks = []
            self._user_defined_states = []
            self._submodules = []
            self._zones = []

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
                    device = {
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
                    _measurements.append(device)
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
        """Transform zone data with optimized dictionary lookups."""
        zones = []
        
        # Pre-build lookup dictionaries for O(1) access
        function_blocks_dict = {v['id']: v['attributes'] for v in self._function_blocks}
        submodules_dict = {v['id']: v['attributes']['application'] for v in self._submodules}

        for zone in data:
            zone_id = zone['id']
            
            # Skip special zone
            if zone_id == '65534' or zone_id == 65534:
                continue

            _applications = {}
            zone_attrs = zone.get('attributes', {})
            
            # Initialize applications
            for application in zone_attrs.get('applications', []):
                _applications[application] = []

            # Process submodules
            for submodule in zone_attrs.get("submodules", []):
                function_attrs = function_blocks_dict.get(submodule)
                if function_attrs and "outputs" in function_attrs:
                    submodule_app = submodules_dict.get(submodule)
                    if submodule_app and submodule_app in _applications:
                        _applications[submodule_app].append(submodule)

            # Only add zones with names
            if "name" in zone_attrs:
                zones.append({
                    "id": zone_id,
                    "name": zone_attrs["name"],
                    "devices": _applications
                })
        
        self._zones = zones
