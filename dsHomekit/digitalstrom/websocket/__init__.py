import _thread
import json
import logging
import time

import websocket

from dsHomekit.config import read_config_file as c, args
from dsHomekit.helper import remove_control_characters


def start_websocket():
    config_file = c()
    if config_file['token']:
        dswebsocket = DsWebsocket()
        _thread.start_new_thread(dswebsocket.start, ())


class DsWebsocket(object):
    def __init__(self):
        self.wshost = "ws://{0}:{1}/api/v1/apartment/notifications".format(
            args.hostname, args.ws_port)

    @staticmethod
    def on_message(ws, message):

        _message = json.loads(remove_control_characters(message))
        if "arguments" in _message:
            if _message['arguments'][0]['type'] == 'apartmentStatusChanged':
                logging.debug("Apartment status changed")

                from ..device_collector import DssCollector
                collector = DssCollector()
                collector.gather_devices_status()

            if _message['arguments'][0]['type'] == 'apartmentStructureChanged':
                logging.debug("Apartment structure changed")

                # homekit.stop()
                time.sleep(2)
                # _thread.start_new_thread(run_homekit, ())

    def on_open(self, ws):
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
