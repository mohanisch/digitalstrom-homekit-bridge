import json

from .const import SMART_HOME_API
from ..config import args
from .device_collector import DssCollector
from .request_handler import DsRequest

dsrequest = DsRequest("https://" + args.hostname + ":" + args.http_port + "/")
collector = DssCollector()


def patch_device(dsuid: str, attributes: dict):
    device_attributes = []
    for output_id, value in attributes.items():
        device_attribute = {
            "op": "replace",
            "path": "/functionBlocks/" + dsuid + "/outputs/" + output_id + "/value",
            "value": str(value)
        }
        device_attributes.append(device_attribute)

    # device_scenario = {
    #     "context": "applicationDevice",
    #     "actionId": "on" if value == 100 else "off",
    #     "application": "",
    #     "area": "",
    #     "zone": "",
    #     "dsDevice": dsuid
    # }

    # if output_id == 'brightness' and (value == 100 or value == 0):
    #     payload_raw.append(device_scenario)
    #     payload = json.dumps(device_scenario).encode("UTF-8")
    #     s.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
    # else:

    payload = json.dumps(device_attributes).encode("UTF-8")
    dsrequest.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)


def patch_switch(user_defined_state_id: str, state: bool):
    print(user_defined_state_id, state)
    switch_attributes = {
        "op": "replace",
        "path": "/status",
        "value": "active" if state else "inactive"
    }
    payload_raw = [switch_attributes]
    payload = json.dumps(payload_raw).encode("UTF-8")
    dsrequest.patch('userDefinedStates/' + user_defined_state_id + '/status', payload=payload)
