"""Extend the basic Accessory and Bridge functions."""
import logging
import threading
import time
from typing import Any

from pyhap.accessory import get_topic
from pyhap.accessory_driver import AccessoryDriver, _wrap_char_setter, _wrap_acc_setter, _wrap_service_setter
from pyhap.const import HAP_REPR_AID, HAP_REPR_IID, HAP_REPR_PID, HAP_REPR_CHARS, HAP_SERVER_STATUS, \
    HAP_PERMISSION_NOTIFY, HAP_REPR_VALUE, HAP_REPR_STATUS

from dsHomekit.utils.registry import Registry

TYPES = Registry()

logger = logging.getLogger(__name__)

def get_accessory(driver, device, aid):
    """Take state and return an accessory object if supported."""
    a_type = None
    name = device['name']

    if device['service'] == "alarm_control_panel":
        a_type = "SecuritySystem"

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

    elif device['service'] in (
            "automation",
            "button",
            "input_boolean",
            "input_button",
            "remote",
            "scene",
            "script",
    ):
        a_type = "Switch"

    if a_type is None:
        return None

    logging.info('Add "%s (%s)" as "%s"', name, device['dsuid'], a_type)
    return TYPES[a_type](driver, name, aid, device=device)


class HomeDriver(AccessoryDriver):
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

        from dsHomekit.digitalstrom import event_decider
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
