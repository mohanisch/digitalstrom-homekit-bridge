from dsbridge.digitalstrom.helper import generate_dsuid


class Apartment(object):
    def __init__(self, apartment_id, data):
        self.apartment_id = apartment_id
        self.data = data

    def gather_state(self, timestamp):
        _dsuid = generate_dsuid(self.apartment_id)
        _apartment_states = {}

        _absent_state = self.data['access']['absent']
        _entity_id = _dsuid + ".switch"
        _apartment_states[_entity_id] = {
            "state": "on" if _absent_state else "off",
            "last_change": timestamp
        }

        for measurement, value in self.data['measurements'].items():
            _service = measurement
            _value = value
            _entity_id = _dsuid + "." + _service
            _apartment_states[_entity_id] = {
                "states": {measurement: {"value": _value}},
                "last_change": timestamp
            }
        return _apartment_states

    def get_entities(self):
        _apartment_states = []
        _apartment_data = self.data

        _dsuid = generate_dsuid(self.apartment_id)
        for measurement in self.data['measurements']:
            d = {
                "entity_id": _dsuid + "." + measurement,
                "dsuid": _dsuid,
                "name": "Apartment " + measurement.capitalize(),
                "service": "sensor",
                "chars": [measurement.capitalize()],
                "support": None,
                "zone": "Apartment",
                "application": measurement
            }
            _apartment_states.append(d)

        d = {
            "entity_id": _dsuid + ".switch",
            "dsuid": "apartmentAbsents",
            "name": "Abwesend",
            "application": "absent",
            "service": "switch",
            "chars": None,
            "support": None,
            "zone": "Apartment",
        }
        _apartment_states.append(d)
        return _apartment_states


class OutputDevices(object):
    def __init__(self, data) -> None:
        self.data = data

    def gather_state(self, timestamp, extra_data):
        _devices = {}
        for device in self.data:
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
                application = ({v['id']: v['attributes']['application'] for v in extra_data}).get(device['id'])

                _entity_id = device['attributes']['functionBlocks'][0]['id'] + "." + str(application)
                d = {_entity_id: {
                    "states": _states,
                    "attributes": _attributes,
                    "last_change": timestamp
                }}
                _devices.update(d)
        return _devices

    def get_entities(self):
        return None


class UserDefinedStates(object):
    def __init__(self, data):
        self.data = data

    def gather_state(self, timestamp):
        _user_defined_states = {}
        for user_state in self.data:
            _dsuid = generate_dsuid(user_state['id'])
            _user_defined_states[_dsuid + ".manualState"] = {
                "state": "on" if user_state['attributes']['status'] == "active" else "off",
                "last_change": timestamp
            }
        return _user_defined_states

    def get_entities(self):
        _user_defined_states = []

        for user_defined_state in self.data:
            if user_defined_state['attributes']['visibleForUsers']:
                d = {
                    "entity_id": generate_dsuid(user_defined_state['id']) + "." + user_defined_state['type'],
                    "dsuid": user_defined_state['id'],
                    "name": user_defined_state['attributes']['name'],
                    "application": user_defined_state['type'],
                    "service": user_defined_state['type'],
                    "chars": None,
                    "support": None,
                    "zone": "Benutzerdefinierte Zustände",
                    "model": "Benutzerdefinierte Zustand"
                }
                _user_defined_states.append(d)
        return _user_defined_states
