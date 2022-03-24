import logging
import websocket
import _thread
import json

from dsHomekit import config
from dsHomekit.digitalstrom.device_collector import DssCollector
from .const import SMART_HOME_API

from .request_handler import DsRequest
from ..config import args

s = DsRequest("https://" + args.hostname + ":" + args.http_port + "/")


collector = DssCollector()

import unicodedata
def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


class DsWebsocket(object):
    def __init__(self):
        self.wshost = "ws://{0}:{1}/api/v1/apartment/notifications".format(
            config.args.hostname, config.args.ws_port)

    @staticmethod
    def on_message(ws, message):
        _devices_updates = []
        _changed_devices = []

        _message = json.loads(remove_control_characters(message))

        if "arguments" in _message:
            if _message['arguments'][0]['type'] == 'apartmentStatusChanged':
                logging.debug("Apartment status changed")
                collector.gather_devices_status()

            if _message['arguments'][0]['type'] == 'apartmentStructureChanged':
                logging.debug("Apartment structure changed")

    def on_error(self, ws, error):
        logging.error(error)

    def on_close(self, ws, close_status_code, close_msg):
        logging.info("Close websocket: " + str(close_status_code))

    def on_open(self, ws):
        def run():
            obj = {
                "protocol": "json",
                "version": 1
            }
            ws.send(json.dumps(obj))

            from dsHomekit import homekit
            homekit.start()

        logging.info("Start websocket client")
        _thread.start_new_thread(run, ())

    def start(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            self.wshost,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()


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
    s.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)


def patch_switch(user_defined_state_id: str, state: bool):
    print(user_defined_state_id, state)
    switch_attributes = {
        "op": "replace",
        "path": "/status",
        "value": "active" if state else "inactive"
    }
    payload_raw = [switch_attributes]
    payload = json.dumps(payload_raw).encode("UTF-8")
    s.patch('userDefinedStates/' + user_defined_state_id + '/status', payload=payload)
