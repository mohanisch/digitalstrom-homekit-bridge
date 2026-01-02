"""
Event patcher for digitalStrom API with error handling.

"""
import json
import logging

from .const import SMART_HOME_API
from ..helper import threaded

logger = logging.getLogger(__name__)


class EventPatcher:
    """Handles patching events to digitalStrom API."""

    def __init__(self):
        """Initialize EventPatcher with request handler."""
        from ..config import args, read_config_file as config_file
        try:
            config = config_file()
            if 'token' not in config or not config['token']:
                raise ValueError("No token found in configuration")

            from .request_handler import RequestHandler
            self.request_handler = RequestHandler(
                "https://" + args.dss_hostname + ":" + args.dss_http_port,
                config['token']
            )
        except Exception as e:
            logger.error("Error initializing EventPatcher: %s", e, exc_info=True)
            raise

    @threaded
    def patch_zone(self, zoneid: int, application: str, actionid: str):
        """Patch zone scenario with error handling."""
        try:
            zone_scenario = {
                "context": "applicationZone",
                "actionId": actionid,
                "application": application,
                "zone": zoneid
            }
            payload = json.dumps(zone_scenario).encode("UTF-8")
            logger.debug("(patch_zone) Payload: %s", payload)

            self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
        except Exception as e:
            logger.error(
                "Error patching zone %d, application %s, action %s: %s",
                zoneid,
                application,
                actionid,
                e,
                exc_info=True
            )

    @threaded
    def patch_device_scenario(self, dsuid: str, actionid: str = ""):
        """Patch device scenario with error handling."""
        try:
            device_scenario = {
                "context": "applicationDevice",
                "actionId": actionid,
                "dsDevice": dsuid
            }
            payload = json.dumps(device_scenario).encode("UTF-8")
            logger.debug("(patch_device_scenarios) Payload: %s", payload)

            self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
        except Exception as e:
            logger.error(
                "Error patching device scenario %s, action %s: %s",
                dsuid,
                actionid,
                e,
                exc_info=True
            )

    @threaded
    def patch_device_status(self, dsuid: str, attributes: dict):
        """Patch device status with error handling."""
        try:
            device_attributes = []
            for output_id, value in attributes.items():
                # Convert brightness and colortemp to integer (digitalSTROM API expects integer values)
                if output_id in ('brightness', 'colortemp') and isinstance(value, (int, float)):
                    value = int(round(value))
                device_attribute = {
                    "op": "replace",
                    "path": "/functionBlocks/" + dsuid + "/outputs/" + output_id + "/value",
                    "value": str(value)
                }
                device_attributes.append(device_attribute)

            payload = json.dumps(device_attributes).encode("UTF-8")
            logger.debug("(patch_device) Payload: %s", payload)

            self.request_handler.patch(SMART_HOME_API + '/dsDevices/' + dsuid + '/status', data=payload)
        except Exception as e:
            logger.error(
                "Error patching device status %s: %s",
                dsuid,
                e,
                exc_info=True
            )

    def patch_switch(self, switch_id: str, state):
        """Patch switch state with error handling."""
        try:
            if switch_id in 'apartmentAbsents':
                switch_scenario = {
                    "context": "applicationApartment",
                    "actionId": state,
                    "application": "access"
                }
                payload = json.dumps(switch_scenario).encode("UTF-8")
                logger.debug("(patch_switch) Payload: %s", payload)

                self.request_handler.post(SMART_HOME_API + '/scenarios/invoke', data=payload)
            else:
                switch_attribute = {
                    "op": "replace",
                    "path": "/status",
                    "value": state
                }
                switch_attributes = [switch_attribute]
                payload = json.dumps(switch_attributes).encode("UTF-8")
                logger.debug("(patch_switch) Payload: %s", payload)

                self.request_handler.patch(
                    SMART_HOME_API + '/userDefinedStates/' + switch_id + '/status',
                    data=payload
                )
        except Exception as e:
            logger.error(
                "Error patching switch %s to state %s: %s",
                switch_id,
                state,
                e,
                exc_info=True
            )
