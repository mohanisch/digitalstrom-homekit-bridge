import json
import logging

from ..helper import threaded
from .const import SMART_HOME_API, SYSTEM_API
from .device_collector import DssCollector


class EventPatcher(object):
    def __init__(self):
        from ..config import args, read_config_file as config_file
        config_file = config_file()
        from .request_handler import DsRequest  # TODO: Gefällt mir nicht
        self.request_handler = DsRequest("https://" + args.hostname + ":" + args.http_port + "/",
                                         config_file['token'])  # TODO: Gefällt mir nicht

    @threaded
    def patch_zone(self, zoneid: int, application: str, actionid: str):
        zone_scenario = {
            "context": "applicationZone",
            "actionId": actionid,
            "application": application,
            "zone": zoneid
        }
        payload = json.dumps(zone_scenario).encode("UTF-8")
        logging.debug("(patch_zone) Payload: %s", payload)

        self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)

    @threaded
    def patch_device_scenario(self, dsuid: str, actionid: str = ""):
        device_scenario = {
            "context": "applicationDevice",
            "actionId": actionid,
            "dsDevice": dsuid
        }
        payload = json.dumps(device_scenario).encode("UTF-8")
        logging.debug("(patch_device_scenarios) Payload: %s", payload)

        self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)

    @threaded
    def patch_device_status(self, dsuid: str, attributes: dict):
        device_attributes = []
        for output_id, value in attributes.items():
            _set_attributes = True
            device_attribute = {
                "op": "replace",
                "path": "/functionBlocks/" + dsuid + "/outputs/" + output_id + "/value",
                "value": str(value)
            }
            device_attributes.append(device_attribute)

        payload = json.dumps(device_attributes).encode("UTF-8")
        logging.debug("(patch_device) Payload: %s", payload)

        self.request_handler.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)

    def patch_switch(self, switch_id: str, state: bool):
        switch_attributes = []
        if switch_id in ('apartmentAbsents', 'dummy'):
            switch_scenario = {
                "context": "applicationApartment",
                "actionId": "absent" if state else "present",
                "application": "access"
            }
            payload = json.dumps(switch_scenario).encode("UTF-8")
            logging.debug("(patch_switch) Payload: %s", payload)

            self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
        else:
            switch_attribute = {
                "op": "replace",
                "path": "/status",
                "value": "active" if state else "inactive"
            }
            switch_attributes.append(switch_attribute)
            payload = json.dumps(switch_attributes).encode("UTF-8")
            logging.debug("(patch_switch) Payload: %s", payload)

            self.request_handler.patch(SMART_HOME_API + '/userDefinedStates/' + switch_id + '/status', data=payload)
