from __future__ import annotations

import logging
import time
from typing import Any, cast
from uuid import UUID

from pyhap.util import callback as pyhap_callback
from pyhap.accessory import Accessory, get_topic, Bridge
from pyhap.accessory_driver import AccessoryDriver, _wrap_char_setter, _wrap_acc_setter, _wrap_service_setter
from pyhap.const import HAP_REPR_AID, HAP_REPR_IID, HAP_REPR_PID, HAP_REPR_CHARS, HAP_SERVER_STATUS, \
    HAP_PERMISSION_NOTIFY, HAP_REPR_VALUE, HAP_REPR_STATUS, CATEGORY_OTHER

from .util import Registry, async_show_setup_message, async_suppress_setup_message
from ..const import BRIDGE_SERIAL_NUMBER, BRIDGE_NAME, MANUFACTURER

TYPES = Registry()

logger = logging.getLogger(__name__)


def get_accessory(driver, device, aid):
    from . import type_lights, type_windowcover, type_sensors, type_switch, type_valve, type_speaker
    """Take state and return an accessory object if supported."""
    a_type = None

    if device['service'] == "sprinkler":
        a_type = "Sprinkler"

    if device['service'] == "audio":
        a_type = "Speaker"

    elif device['service'] == "shades":
        a_type = "WindowCovering"

    elif device['service'] == "lights":
        a_type = "Light"

    elif device['service'] == "sensor":
        if 'Temperature' in device['chars']:
            a_type = "TemperatureSensor"
        elif 'Humidity' in device['chars']:
            a_type = "HumiditySensor"
        elif 'Brightness' in device['chars']:
            a_type = "LightSensor"
        elif 'Motion' in device['chars']:
            a_type = "MotionSensor"

    elif device['service'] in (
            "automation",
            "button",
            "switch",
            "input_boolean",
            "input_button",
            "remote",
            "scene",
            "script",
    ):
        a_type = "Switch"

    if a_type is None:
        return None

    logging.info('Add "%s (%s)" as "%s"', device['name'], device['entity_id'], a_type)
    return TYPES[a_type](driver, device['name'], aid, device['entity_id'], device)


class DsAccessory(Accessory):
    def __init__(
        self,
        driver: DsAccessoryDriver,
        name: str,
        aid: int,
        entity_id: str,
        config: dict,
        *args: Any,
        category: str = CATEGORY_OTHER,
        **kwargs: Any,
    ) -> None:
        """Initialize a Accessory object."""
        super().__init__(
            driver=driver,
            display_name=name,
            aid=aid
        )
        self.category = category

        self.config = config
        self.entity_id = entity_id
        self.application = self.config['application']

        if 'zoneid' in config:
            self.zoneid = self.config['zoneid']
        else:
            self.zoneid = 0
        if 'dsuid' in config:
            self.dsuid = config['dsuid']
        if 'chars' in config:
            self.chars = config['chars']
        if 'support' in config:
            self.support = config['support']


class DsAccessoryDriver(AccessoryDriver):
    """Adapter class for AccessoryDriver."""

    def __init__(
            self,
            **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)

    def set_characteristics(self, chars_query, client_addr):
        """Called from ``HAPServerHandler`` when iOS configures the characteristics.

        :param chars_query: A configuration query. For example:

        .. code-block:: python

           {
              "characteristics": [{
                 "aid": 1,
                 "iid": 2,
                 "value": False, # Value to set
                 "ev": True # (Un)subscribe for events from this characteristics.
              }]
           }

        :type chars_query: dict
        """
        # TODO: Add support for chars that do no support notifications.
        updates = {}
        setter_results = {}
        had_error = False
        expired = False

        if HAP_REPR_PID in chars_query:
            pid = chars_query[HAP_REPR_PID]
            expire_time = self.prepared_writes.get(client_addr, {}).pop(pid, None)
            if expire_time is None or time.time() > expire_time:
                expired = True

        from . import event_decider
        event_decider.recieve_hap_event(chars_query['characteristics'])

        for cq in chars_query[HAP_REPR_CHARS]:
            aid, iid = cq[HAP_REPR_AID], cq[HAP_REPR_IID]
            setter_results.setdefault(aid, {})

            if expired:
                setter_results[aid][iid] = HAP_SERVER_STATUS.INVALID_VALUE_IN_REQUEST
                had_error = True
                continue

            if HAP_PERMISSION_NOTIFY in cq:
                char_topic = get_topic(aid, iid)
                action = "Subscribed" if cq[HAP_PERMISSION_NOTIFY] else "Unsubscribed"
                logger.debug(
                    "%s client %s to topic %s", action, client_addr, char_topic
                )
                self.async_subscribe_client_topic(
                    client_addr, char_topic, cq[HAP_PERMISSION_NOTIFY]
                )

            if HAP_REPR_VALUE not in cq:
                continue

            updates.setdefault(aid, {})[iid] = cq[HAP_REPR_VALUE]

        for aid, new_iid_values in updates.items():
            if self.accessory.aid == aid:
                acc = self.accessory
            else:
                acc = self.accessory.accessories.get(aid)

            updates_by_service = {}
            char_to_iid = {}
            for iid, value in new_iid_values.items():
                # Characteristic level setter callbacks
                char = acc.get_characteristic(aid, iid)

                set_result = _wrap_char_setter(char, value, client_addr)
                if set_result != HAP_SERVER_STATUS.SUCCESS:
                    had_error = True
                setter_results[aid][iid] = set_result

                if not char.service or (
                        not acc.setter_callback and not char.service.setter_callback
                ):
                    continue
                char_to_iid[char] = iid
                updates_by_service.setdefault(char.service, {}).update({char: value})

            # Accessory level setter callbacks
            if acc.setter_callback:
                set_result = _wrap_acc_setter(acc, updates_by_service, client_addr)
                if set_result != HAP_SERVER_STATUS.SUCCESS:
                    had_error = True
                for iid in updates[aid]:
                    setter_results[aid][iid] = set_result

            # Service level setter callbacks
            for service, chars in updates_by_service.items():
                if not service.setter_callback:
                    continue
                set_result = _wrap_service_setter(service, chars, client_addr)
                if set_result != HAP_SERVER_STATUS.SUCCESS:
                    had_error = True
                for char in chars:
                    setter_results[aid][char_to_iid[char]] = set_result

        if not had_error:
            return None

        return {
            HAP_REPR_CHARS: [
                {
                    HAP_REPR_AID: aid,
                    HAP_REPR_IID: iid,
                    HAP_REPR_STATUS: status,
                }
                for aid, iid_status in setter_results.items()
                for iid, status in iid_status.items()
            ]
        }

    @pyhap_callback
    def pair(
        self, client_uuid: UUID, client_public: str, client_permissions: int
    ) -> bool:
        """Override super function to dismiss setup message if paired."""
        success = super().pair(client_uuid, client_public, client_permissions)
        if success:
            async_suppress_setup_message()
        return cast(bool, success)

    @pyhap_callback
    def unpair(self, client_uuid: UUID) -> None:
        """Override super function to show setup message if unpaired."""
        super().unpair(client_uuid)

        if self.state.paired:
            return

        async_show_setup_message(
            "self._entry_id",
            "accessory_friendly_name(self._entry_title, self.accessory)",
            self.state.pincode,
            self.accessory.xhm_uri(),
        )


class DsBridge(Bridge):
    def __init__(
            self, driver: DsAccessoryDriver, name: str
    ):
        super().__init__(driver, name)
        self.set_info_service(
            model=BRIDGE_NAME,
            manufacturer=MANUFACTURER,
            firmware_revision=BRIDGE_SERIAL_NUMBER,
            serial_number=BRIDGE_SERIAL_NUMBER,
        )

    def setup_message(self) -> None:
        """Avoid that the Pyhap setup message appears on the terminal"""

