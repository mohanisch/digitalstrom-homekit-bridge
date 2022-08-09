from dsbridge.digitalstrom.helper import generate_dsuid


class Apartment(object):
    def __init__(self, id, data):
        self.apartmentid = id
        self.data = data

    def gather_state(self, timestamp):
        _dsuid = generate_dsuid(self.apartmentid)
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

        _dsuid = generate_dsuid(self.apartmentid)
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
