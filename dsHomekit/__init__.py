import json
import logging

from .digitalstrom import collector
from .homekit import homekit
from dsHomekit import config

import websocket
import _thread
from .utils.helper import remove_control_characters


def _loglevel():
    loglevel = config.args.loglevel.upper()
    if 'loglevel' in config.file:
        loglevel = config.file['loglevel'].upper()
    return loglevel


logging.basicConfig(
    level=getattr(logging, _loglevel()),
    format='%(asctime)s %(name)s.%(funcName)s : %(levelname)-8s [%(process)d] %(message)s',
)


def add_devices():
    dsdevices = collector.get_entities()

    for dsdevice in dsdevices:
        homekit.add_bridge_accessory(dsdevice)


def on_open(ws):
    homekit.setup()

    def run():
        obj = {
            "protocol": "json",
            "version": 1
        }
        ws.send(json.dumps(obj))

        add_devices()
        homekit.start()

    logging.info("Start websocket client")
    _thread.start_new_thread(run, ())


class DsWebsocket(object):
    def __init__(self):
        self.wshost = "ws://{0}:{1}/api/v1/apartment/notifications".format(
            config.args.hostname, config.args.ws_port)

    @staticmethod
    def on_message(ws, message):

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
        logging.info("Close websocket")

    def start(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            self.wshost,
            on_open=on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()


dswebsocket = DsWebsocket()
