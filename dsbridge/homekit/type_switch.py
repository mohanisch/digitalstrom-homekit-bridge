import logging
import time

from pyhap.const import CATEGORY_SWITCH

from .const import CHAR_ON, STATE_ON
from ..homekit import collector
from ..homekit.accessories import TYPES, DsAccessory
from ..helper import threaded
from . import event_decider


@TYPES.register("Switch")
class Switch(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SWITCH)

        self.accessory_state = False

        self.states = collector.get_device_state(self.entity_id)

        serv_switch = self.add_preload_service('Switch')
        self.char_on = serv_switch.configure_char(
            CHAR_ON, value=False,
        )

        serv_switch.setter_callback = self._set_chars
        self.async_update_state(self.states)

    @threaded
    def _set_chars(self, char_values):
        logging.debug("Switch _set_chars: %s", char_values)
        _attributes = {}

        if self.char_on.value == 0:
            self.accessory_state = False
        else:
            self.accessory_state = True

        _attributes.update({'active': char_values[CHAR_ON]})

        event_decider.device_event(
            self.entity_id,
            self.dsuid,
            self.zoneid,
            _attributes,
            self.application
        )

    @DsAccessory.run_at_interval(3)
    async def run(self):

        device_state = collector.get_device_state(self.entity_id)
        current_time = int(time.time())

        _value = device_state['state'] == STATE_ON

        if self.accessory_state != bool(_value) and current_time-3 < device_state['last_change']:
            self.accessory_state = bool(_value)
            self.char_on.set_value(self.accessory_state)

    def async_update_state(self, new_state):
        """Update switch state after state changed."""

        current_state = new_state['state'] == STATE_ON
        self.accessory_state = current_state
        logging.debug("%s: Set current state to %s", self.dsuid, current_state)
        self.char_on.set_value(current_state)
