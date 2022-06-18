import json
import logging
import time

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


def run_homekit():
    homekit.setup()
    add_devices()
    logging.info("Start homekit...")
    homekit.start()


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

                homekit.stop()
                time.sleep(2)
                _thread.start_new_thread(run_homekit, ())

    @staticmethod
    def on_open(ws):

        def run_websocket():
            obj = {
                "protocol": "json",
                "version": 1
            }
            ws.send(json.dumps(obj))



        logging.info("Start websocket client...")
        _thread.start_new_thread(run_websocket, ())

        logging.info("Start homekit...")
        _thread.start_new_thread(run_homekit, ())

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


dswebsocket = DsWebsocket()
