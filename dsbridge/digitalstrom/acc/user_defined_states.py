from dsbridge.digitalstrom.helper import generate_dsuid


class UserDefinedStates:
    def __init__(self, data):
        self.data = data

    def gather_state(self, timestamp):
        _user_defined_states = {}
        for user_state in self.data:
            _dsuid = generate_dsuid(user_state['id'])
            _states = {"on": user_state['attributes']['status'] == "active"}
            _user_defined_states[_dsuid + ".manualState"] = {
                "states": _states,
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
                    "support": {},
                    "zone": "Benutzerdefinierte Zustände",
                    "model": "Benutzerdefinierte Zustand"
                }
                _user_defined_states.append(d)
        return _user_defined_states
