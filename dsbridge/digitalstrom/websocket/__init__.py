import _thread
import json
import logging
import time

import websocket

from .. import state_collector, device_collector
from ...config import read_config_file as c, args
from ...helper import remove_control_characters


def start_websocket():
    config_file = c()
    if config_file['token']:
        dswebsocket = DsWebsocket()
        _thread.start_new_thread(dswebsocket.start, ())


class DsWebsocket(object):
    def __init__(self):
        self.host = "ws://{0}:{1}/api/v1/apartment/notifications".format(args.dss_hostname, args.ws_port)

    def start(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            self.host,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()

    @staticmethod
    def on_message(ws, message):

        _message = json.loads(remove_control_characters(message))
        if "arguments" in _message:
            if _message['arguments'][0]['type'] == 'apartmentStatusChanged':
                logging.debug("Apartment status changed")
                state_collector.gather_devices_status()

            if _message['arguments'][0]['type'] == 'apartmentStructureChanged':
                logging.debug("Apartment structure changed")
                device_collector.load_apartment_data()


    @staticmethod
    def on_open(ws):
        def run_websocket():
            obj = {
                "protocol": "json",
                "version": 1
            }
            ws.send(json.dumps(obj))

        logging.info("Start websocket...")
        run_websocket()

    @staticmethod
    def on_error(ws, error):
        logging.error(error)

    @staticmethod
    def on_close(ws, close_status_code, close_msg):
        logging.info("Close websocket")
