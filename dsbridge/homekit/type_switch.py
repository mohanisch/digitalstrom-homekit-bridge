import logging
import time

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SWITCH

from ..const import CHAR_ON, STATE_ON
from ..homekit import collector
from ..homekit.accessories import TYPES
from ..helper import threaded
from . import event_decider


@TYPES.register("Switch")
class Switch(Accessory):
    category = CATEGORY_SWITCH

    def __init__(self, *args, device=None):
        super().__init__(*args)

        self.chars = device['chars']
        self.dsuid = device['dsuid']
        self.entity_id = device['entity_id']
        self.accessory_state = False

        self.states = collector.get_device_state(self.entity_id)

        serv_switch = self.add_preload_service('Switch')
        self.char_on = serv_switch.configure_char(
            CHAR_ON, value=False,
            # setter_callback=self.set_state
        )

        serv_switch.setter_callback = self._set_chars
        self.async_update_state(self.states)

    @threaded
    def _set_chars(self, char_values):
        logging.debug("Switch _set_chars: %s", char_values)

        if self.char_on.value == 0:
            self.accessory_state = False
        else:
            self.accessory_state = True

        # TODO: Muss anders funktionieren
        event_decider.patch_switch(
            self.dsuid,
            self.accessory_state)

    @Accessory.run_at_interval(3)
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
